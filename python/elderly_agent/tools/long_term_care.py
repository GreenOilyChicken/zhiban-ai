"""
long_term_care — 长护险申请工具

功能：
1. 身份证号校验（18 位校验位 + 地址码 + 出生日期）
2. 身份证号脱敏（始终开启，即使 LTC_LOG_MASK=false）
3. 模拟长护险申请提交（生成申请编号）
4. 输出长护险政策参考

安全要求：
- 身份证号在所有日志和输出中始终脱敏（即使 LTC_LOG_MASK=false）
- 申请编号格式：LTC-{YYYYMMDD}-{6位随机}
"""
from __future__ import annotations

import datetime
import logging
import random
import re
import string
from typing import Dict, Optional

from base.agent_framework import Tool

logger = logging.getLogger(__name__)

# ── 身份证脱敏：始终开启，不受 LTC_LOG_MASK 控制 ─────────

# 身份证校验位权重
_ID_WEIGHTS = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
# 校验位对照表
_ID_CHECK_CODES = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']

# 身份证前 2 位地址码（部分）
_ID_REGION_PREFIX = {
    "11": "北京市", "12": "天津市", "13": "河北省", "14": "山西省",
    "15": "内蒙古自治区", "21": "辽宁省", "22": "吉林省", "23": "黑龙江省",
    "31": "上海市", "32": "江苏省", "33": "浙江省", "34": "安徽省",
    "35": "福建省", "36": "江西省", "37": "山东省", "41": "河南省",
    "42": "湖北省", "43": "湖南省", "44": "广东省", "45": "广西壮族自治区",
    "46": "海南省", "50": "重庆市", "51": "四川省", "52": "贵州省",
    "53": "云南省", "54": "西藏自治区", "61": "陕西省", "62": "甘肃省",
    "63": "青海省", "64": "宁夏回族自治区", "65": "新疆维吾尔自治区",
}


def mask_id_card(id_card: str) -> str:
    """
    身份证号脱敏：始终开启，即使 LTC_LOG_MASK=false
    格式：110105********1234（保留前 6 位和后 4 位）
    """
    if not id_card or len(id_card) < 10:
        return "***"

    id_card = id_card.strip()
    if len(id_card) == 18:
        # 18位：前6 + 中间8位星号 + 后4
        return id_card[:6] + "********" + id_card[-4:]
    elif len(id_card) == 15:
        # 15位老身份证：前4 + 中间7位星号 + 后4
        return id_card[:4] + "*******" + id_card[-4:]
    else:
        return "***"


def _mask_phone(phone: str) -> str:
    """手机号脱敏"""
    if not phone or len(phone) < 7:
        return "***"
    phone = phone.strip()
    if len(phone) == 11:
        return phone[:3] + "****" + phone[-4:]
    return "***"


def _validate_id_card(id_card: str) -> Dict:
    """
    身份证号校验
    Returns: {"valid": bool, "errors": [str], "info": {region, birthday, gender}}
    """
    result = {"valid": True, "errors": [], "info": {}}
    id_card = id_card.strip().upper()

    # 基本格式检查
    if len(id_card) == 15:
        # 15位老身份证
        if not id_card.isdigit():
            result["valid"] = False
            result["errors"].append("15位身份证必须全为数字")
            return result
        # 转换为18位继续校验
        id_card = _convert_15_to_18(id_card)

    if len(id_card) != 18:
        result["valid"] = False
        result["errors"].append(f"身份证号长度应为18位（实际{len(id_card)}位）")
        return result

    # 正则格式检查
    if not re.match(r'^\d{17}[\dX]$', id_card):
        result["valid"] = False
        result["errors"].append("身份证格式不正确（前17位应为数字，末位为数字或X）")
        return result

    # 地址码检查
    region_code = id_card[:2]
    if region_code not in _ID_REGION_PREFIX:
        result["valid"] = False
        result["errors"].append(f"身份证地址码不合法：前两位 {region_code}")
    else:
        result["info"]["region"] = _ID_REGION_PREFIX[region_code]

    # 出生日期检查
    birth_str = id_card[6:14]
    try:
        birth_date = datetime.datetime.strptime(birth_str, "%Y%m%d")
        # 检查日期合理性
        if birth_date.year < 1900 or birth_date > datetime.datetime.now():
            result["valid"] = False
            result["errors"].append(f"出生日期不合理：{birth_str[:4]}-{birth_str[4:6]}-{birth_str[6:8]}")
        else:
            result["info"]["birthday"] = f"{birth_str[:4]}-{birth_str[4:6]}-{birth_str[6:8]}"
            result["info"]["age"] = _calculate_age(birth_date)
    except ValueError:
        result["valid"] = False
        result["errors"].append(f"出生日期无效：{birth_str[:4]}-{birth_str[4:6]}-{birth_str[6:8]}")

    # 校验位验证
    total = 0
    for i in range(17):
        total += int(id_card[i]) * _ID_WEIGHTS[i]
    check_code = _ID_CHECK_CODES[total % 11]
    if id_card[17] != check_code:
        result["valid"] = False
        result["errors"].append(
            f"校验位不正确：末位应为 '{check_code}'，实际为 '{id_card[17]}'"
        )

    # 性别推断
    gender_digit = int(id_card[16])
    result["info"]["gender"] = "男" if gender_digit % 2 == 1 else "女"

    return result


def _convert_15_to_18(id_15: str) -> str:
    """15位身份证转18位"""
    id_17 = "19" + id_15[6:12] + id_15[12:15]
    # 计算校验位
    id_17 = id_15[:6] + "19" + id_15[6:]
    total = 0
    for i in range(17):
        total += int(id_17[i]) * _ID_WEIGHTS[i]
    check_code = _ID_CHECK_CODES[total % 11]
    return id_17 + check_code


def _calculate_age(birth_date: datetime.datetime) -> int:
    """计算周岁"""
    today = datetime.datetime.now()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def _generate_application_id() -> str:
    """生成申请编号：LTC-YYYYMMDD-XXXXXX"""
    today = datetime.datetime.now()
    date_str = today.strftime("%Y%m%d")
    random_part = ''.join(random.choices(string.digits, k=6))
    return f"LTC-{date_str}-{random_part}"


def _validate_phone(phone: str) -> bool:
    """手机号基本校验"""
    phone = phone.strip()
    return bool(re.match(r'^1[3-9]\d{9}$', phone))


# ── 长护险政策参考 ───────────────────────────────────────

_LTC_POLICY_INFO = """【长期护理保险政策参考】

1. 参保条件：
   - 参加城镇职工基本医疗保险或城乡居民基本医疗保险
   - 经评估认定为失能（中度及以上）或失智
   - 连续参保缴费满规定期限（各地不同，通常 6 个月-2 年）

2. 失能等级评估：
   - 轻度失能：日常生活能力部分受损
   - 中度失能：日常生活能力明显受损
   - 重度失能：日常生活能力严重受损，完全依赖他人照护
   - 评估标准采用 ADL（日常生活活动能力量表）和 IADL（工具性日常生活活动能力量表）

3. 待遇类型：
   - 机构照护：入住定点护理机构
   - 居家照护：专业护理人员上门服务
   - 居家补贴：给予家属照护补贴

4. 待遇标准（各地有差异）：
   - 重度失能：机构约 70-100 元/日，居家约 40-60 元/日
   - 中度失能：机构约 40-70 元/日，居家约 20-40 元/日
   - 轻度失能：各地标准不同，部分城市不纳入

5. 申请流程：
   ① 准备材料：身份证、社保卡、病历资料、代办需代办人身份证
   ② 向参保地医保经办机构或社区提交申请
   ③ 专家上门评估失能等级
   ④ 公示评估结果
   ⑤ 签订服务协议，享受待遇

6. 咨询电话：全国统一 12393（医保服务热线）"""


# ── 工具主函数 ───────────────────────────────────────────

def _long_term_care_func(
    applicant_name: str,
    id_card: str,
    contact_phone: str,
    disability_level: str,
    care_type: str = "居家照护",
    agent_name: str = "",
    agent_phone: str = "",
) -> str:
    """
    长护险申请模拟提交。
    applicant_name: 申请人姓名
    id_card: 申请人身份证号
    contact_phone: 联系电话
    disability_level: 失能等级（轻度/中度/重度）
    care_type: 照护类型（机构照护/居家照护）
    agent_name: 代办人姓名（可选）
    agent_phone: 代办人电话（可选）
    """
    lines = []
    lines.append("══════════════════════════════════════")
    lines.append("  长期护理保险申请 — 提交确认")
    lines.append("══════════════════════════════════════")
    lines.append("")

    # 1. 身份证校验
    validation = _validate_id_card(id_card)

    if validation["valid"]:
        lines.append("【身份验证】✓ 通过")
        lines.append(f"  申请人姓名：{applicant_name}")
        lines.append(f"  身份证号（脱敏）：{mask_id_card(id_card)}")
        if validation["info"].get("region"):
            lines.append(f"  籍贯地区：{validation['info']['region']}")
        if validation["info"].get("birthday"):
            lines.append(f"  出生日期：{validation['info']['birthday']}")
            lines.append(f"  年龄：{validation['info']['age']} 岁")
        lines.append(f"  性别：{validation['info']['gender']}")
        lines.append("")
    else:
        lines.append("【身份验证】✗ 不通过")
        lines.append(f"  身份证号（脱敏）：{mask_id_card(id_card)}")
        for err in validation["errors"]:
            lines.append(f"  · {err}")
        lines.append("")
        lines.append("请核对身份证号后重新提交。")
        lines.append("")
        lines.append("══════════════════════════════════════")
        return "\n".join(lines)

    # 2. 失能等级校验
    valid_levels = ["轻度", "中度", "重度"]
    if disability_level not in valid_levels:
        lines.append(f"【失能等级】✗ 不通过")
        lines.append(f"  输入值：{disability_level}（请选择：轻度、中度、重度）")
        lines.append("")
        lines.append("══════════════════════════════════════")
        return "\n".join(lines)

    lines.append(f"【失能等级】{disability_level}")
    lines.append(f"【申请照护类型】{care_type}")
    lines.append("")

    # 3. 联系电话校验
    if not _validate_phone(contact_phone):
        lines.append("【联系电话】✗ 格式不正确")
        lines.append(f"  输入值（脱敏）：{_mask_phone(contact_phone)}")
        lines.append("  请输入正确的 11 位手机号码。")
        lines.append("")
        lines.append("══════════════════════════════════════")
        return "\n".join(lines)

    lines.append(f"【联系电话（脱敏）】{_mask_phone(contact_phone)}")
    lines.append("")

    # 4. 代办人信息（如有）
    if agent_name:
        lines.append(f"【代办人】{agent_name}")
        if agent_phone:
            if _validate_phone(agent_phone):
                lines.append(f"【代办人电话（脱敏）】{_mask_phone(agent_phone)}")
            else:
                lines.append("【代办人电话】✗ 格式不正确")
        lines.append("")

    # 5. 模拟提交
    app_id = _generate_application_id()
    lines.append("【提交结果】")
    lines.append(f"  申请编号：{app_id}")
    lines.append(f"  提交时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  状态：已提交（待评估）")
    lines.append("")

    # 6. 后续流程提示
    lines.append("【后续流程】")
    lines.append("  1. 经办机构将在 10 个工作日内联系您安排上门评估")
    lines.append("  2. 评估专家将使用 ADL/IADL 量表评定失能等级")
    lines.append("  3. 评估结果将在社区公示 5 个工作日")
    lines.append("  4. 公示无异议后签订服务协议，开始享受待遇")
    lines.append("")

    # 7. 政策参考
    lines.append(_LTC_POLICY_INFO)
    lines.append("")

    # 8. 紧急信号
    lines.append("【紧急联系方式】")
    lines.append("  · 急救电话：120")
    lines.append("  · 心理援助热线：400-161-9995")
    lines.append("  · 医保服务热线：12393")
    lines.append("══════════════════════════════════════")
    lines.append("")
    lines.append("⚠️ 此为模拟申请，仅用于演示。正式申请请前往当地医保经办机构办理。")

    # 日志记录（脱敏后的信息）
    logger.info(
        f"长护险申请模拟提交: app_id={app_id}, "
        f"applicant={applicant_name}, id={mask_id_card(id_card)}, "
        f"level={disability_level}, care_type={care_type}"
    )

    return "\n".join(lines)


# ── Tool 工厂 ───────────────────────────────────────────

def build_long_term_care_tool() -> Tool:
    """构建长护险申请工具"""
    return Tool(
        name="long_term_care",
        description=(
            "长期护理保险申请模拟工具。输入申请人姓名、身份证号、联系电话、"
            "失能等级等，进行身份校验后生成模拟申请提交。"
            "身份证号和手机号在输出中始终脱敏。"
        ),
        func=_long_term_care_func,
        param_descriptions={
            "applicant_name": {
                "description": "申请人姓名",
                "required": True,
            },
            "id_card": {
                "description": "申请人身份证号（18位，身份证号在输出中始终脱敏）",
                "required": True,
            },
            "contact_phone": {
                "description": "联系电话（11位手机号）",
                "required": True,
            },
            "disability_level": {
                "description": "失能等级：轻度/中度/重度",
                "required": True,
            },
            "care_type": {
                "description": "申请照护类型：机构照护/居家照护（默认居家照护）",
                "required": False,
            },
            "agent_name": {
                "description": "代办人姓名（可选）",
                "required": False,
            },
            "agent_phone": {
                "description": "代办人电话（可选）",
                "required": False,
            },
        },
    )
