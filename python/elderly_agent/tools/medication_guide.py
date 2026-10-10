"""
medication_guide — 老年人用药指导工具

功能：
1. DDI（药物-药物相互作用）矩阵查询
2. 单药剂量异常检测（老年人群安全剂量范围）
3. 疾病-药物禁忌检查
4. 所有输出附带医疗免责声明

安全要求：
- 所有药物建议仅供参考，不替代医师处方
- 输出中始终包含紧急信号（120 急救 / 心理援助热线 400-161-9995）
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from base.agent_framework import Tool

logger = logging.getLogger(__name__)

# ── 医疗免责声明（所有药物输出必附）──────────────────────

MEDICAL_DISCLAIMER = (
    "\n\n⚠️ 医疗免责声明：以上用药信息仅供参考，不能替代执业医师面诊和处方。"
    "如出现药物不良反应或紧急情况，请立即拨打 120 急救电话。"
    "如遇心理危机，请拨打心理援助热线 400-161-9995。"
)

# ── DDI 药物-药物相互作用矩阵 ────────────────────────────
# key = (药A通用名, 药B通用名), value = 相互作用描述 + 严重程度

_DDI_MATRIX: Dict[tuple, dict] = {
    # ── 抗凝/抗血小板药物组合 ──
    ("华法林", "阿司匹林"): {
        "severity": "严重",
        "description": "华法林与阿司匹林合用显著增加出血风险（消化道出血、脑出血）。"
                       "需密切监测 INR 值，一般避免联用；如需联用应使用最低有效剂量并加用 PPI 护胃。",
        "action": "建议医师评估出血风险，监测 INR，考虑替代方案。",
    },
    ("华法林", "氯吡格雷"): {
        "severity": "严重",
        "description": "华法林联合氯吡格雷出血风险极高，尤其老年人。仅用于特定适应症（如机械瓣膜+支架术后）。",
        "action": "必须在专科医师指导下使用，每周监测 INR。",
    },
    ("阿司匹林", "氯吡格雷"): {
        "severity": "中等",
        "description": "双联抗血小板治疗增加出血风险，老年人需评估消化道出血风险，"
                       "建议联用质子泵抑制剂（如泮托拉唑）。",
        "action": "评估 DAPT 持续时间，必要时使用 PPI 保护胃黏膜。",
    },
    ("华法林", "利伐沙班"): {
        "severity": "严重",
        "description": "华法林与 DOAC（利伐沙班）合用无临床获益且严重增加出血风险，属禁忌组合。",
        "action": "绝对禁止联用，如需转换抗凝方案需桥接过渡。",
    },

    # ── NSAIDs 组合 ──
    ("布洛芬", "阿司匹林"): {
        "severity": "中等",
        "description": "布洛芬可减弱阿司匹林的心血管保护作用（竞争结合 COX-1），"
                       "同时增加消化道出血风险。",
        "action": "如需止痛，建议在服用阿司匹林后至少 2 小时再服布洛芬，或选用对乙酰氨基酚。",
    },
    ("布洛芬", "华法林"): {
        "severity": "严重",
        "description": "NSAIDs 联合华法林显著增加消化道出血风险。",
        "action": "避免联用，必要时使用对乙酰氨基酚替代布洛芬。",
    },
    ("双氯芬酸", "阿司匹林"): {
        "severity": "中等",
        "description": "双氯芬酸联合阿司匹林增加消化道出血和肾损伤风险。",
        "action": "老年人慎用，建议选用对乙酰氨基酚。",
    },

    # ── 心血管药物组合 ──
    ("美托洛尔", "维拉帕米"): {
        "severity": "严重",
        "description": "β受体阻滞剂联合非二氢吡啶类钙通道阻滞剂可导致严重心动过缓、"
                       "房室传导阻滞、低血压，老年人尤需警惕。",
        "action": "避免联用，如必须使用需心电监测并调整剂量。",
    },
    ("美托洛尔", "地尔硫卓"): {
        "severity": "严重",
        "description": "同上，β受体阻滞剂联合地尔硫卓可致严重心动过缓和传导阻滞。",
        "action": "避免联用，必要时换用二氢吡啶类 CCB（如氨氯地平）。",
    },
    ("氨氯地平", "辛伐他汀"): {
        "severity": "中等",
        "description": "氨氯地平可升高辛伐他汀血药浓度，增加横纹肌溶解风险。"
                       "辛伐他汀日剂量不应超过 20mg（与氨氯地平台用时）。",
        "action": "限制辛伐他汀剂量 ≤20mg/日，或换用不经 CYP3A4 代谢的他汀（如瑞舒伐他汀）。",
    },
    ("呋塞米", "赖诺普利"): {
        "severity": "中等",
        "description": "ACE抑制剂联合利尿剂可引起首剂低血压效应，老年人尤其明显。"
                       "且可能引起肾功能急剧下降。",
        "action": "起始小剂量，监测血压和肾功能、电解质（尤其钾离子）。",
    },

    # ── 降糖药组合 ──
    ("二甲双胍", "格列美脲"): {
        "severity": "中等",
        "description": "联用增加低血糖风险，尤其是老年人肾功能下降时。"
                       "二甲双胍本身在老年人需根据 eGFR 调整剂量。",
        "action": "监测血糖，老年人格列美脲起始剂量减半，评估 eGFR。",
    },
    ("胰岛素", "二甲双胍"): {
        "severity": "低",
        "description": "联用通常安全且常见，但需注意低血糖风险随年龄增加而上升。",
        "action": "常规监测血糖，老年患者设定相对宽松的降糖目标。",
    },

    # ── 精神类药物组合 ──
    ("地西泮", "佐匹克隆"): {
        "severity": "严重",
        "description": "两种中枢镇静药联用可致过度镇静、呼吸抑制、跌倒风险显著升高，"
                       "老年人应避免联用。",
        "action": "避免联用，如需催眠药仅保留一种，并使用最低有效剂量。",
    },
    ("帕罗西汀", "曲马多"): {
        "severity": "严重",
        "description": "帕罗西汀（SSRI）联合曲马多增加 5-羟色胺综合征风险，"
                       "表现为震颤、出汗、肌阵挛、高热，可危及生命。",
        "action": "避免联用，如需止痛可考虑对乙酰氨基酚或非阿片类镇痛药。",
    },
    ("舍曲林", "曲马多"): {
        "severity": "严重",
        "description": "同帕罗西汀-曲马多相互作用，5-羟色胺综合征风险。",
        "action": "避免联用，咨询药师替代镇痛方案。",
    },
    ("地西泮", "苯海拉明"): {
        "severity": "中等",
        "description": "苯海拉明有抗胆碱能作用，联用苯二氮卓类可叠加中枢抑制，"
                       "老年人认知障碍和跌倒风险增加。",
        "action": "避免联用，老年人慎用第一代抗组胺药。",
    },

    # ── 其他常见组合 ──
    ("奥美拉唑", "氯吡格雷"): {
        "severity": "中等",
        "description": "奥美拉唑（CYP2C19 抑制剂）可降低氯吡格雷活化，减弱抗血小板效果。"
                       "泮托拉唑或雷贝拉唑影响较小。",
        "action": "如需 PPI 护胃，优选泮托拉唑。",
    },
    ("左甲状腺素", "碳酸钙"): {
        "severity": "低",
        "description": "碳酸钙可减少左甲状腺素吸收，导致甲减控制不佳。",
        "action": "两者间隔至少 4 小时服用。",
    },
    ("左甲状腺素", "铁剂"): {
        "severity": "低",
        "description": "铁剂可与左甲状腺素形成络合物，影响吸收。",
        "action": "两者间隔至少 4 小时服用。",
    },
}

# ── 老年人单药安全剂量参考 ───────────────────────────────
# 用于剂量异常检测：超过 max_daily_dose 触发警告

_MEDICATION_DOSE_REF: Dict[str, dict] = {
    "阿司匹林": {
        "common_dose": "75-100mg/次，每日1次（心血管二级预防）",
        "max_daily_dose": 300,
        "unit": "mg",
        "elderly_note": "老年人一级预防需评估出血风险，不常规推荐。",
    },
    "华法林": {
        "common_dose": "2.5-5mg/日起始，根据 INR 调整",
        "max_daily_dose": 10,
        "unit": "mg",
        "elderly_note": "老年人起始剂量偏低（2-3mg），需定期监测 INR（目标 2.0-3.0）。",
    },
    "二甲双胍": {
        "common_dose": "500mg/次，每日2-3次",
        "max_daily_dose": 2000,
        "unit": "mg",
        "elderly_note": "eGFR<45 时减量，eGFR<30 禁用。",
    },
    "格列美脲": {
        "common_dose": "1-2mg/日起始",
        "max_daily_dose": 6,
        "unit": "mg",
        "elderly_note": "老年人起始 0.5-1mg，低血糖风险高，优选 DPP-4 抑制剂替代。",
    },
    "美托洛尔": {
        "common_dose": "缓释片 23.75-47.5mg/次，每日1次",
        "max_daily_dose": 190,
        "unit": "mg",
        "elderly_note": "老年人注意心动过缓和传导阻滞。",
    },
    "氨氯地平": {
        "common_dose": "2.5-5mg/次，每日1次",
        "max_daily_dose": 10,
        "unit": "mg",
        "elderly_note": "老年人起始 2.5mg，注意下肢水肿。",
    },
    "阿托伐他汀": {
        "common_dose": "10-20mg/次，每晚1次",
        "max_daily_dose": 40,
        "unit": "mg",
        "elderly_note": "老年人注意肌肉疼痛、肝功能异常。",
    },
    "辛伐他汀": {
        "common_dose": "10-20mg/次，每晚1次",
        "max_daily_dose": 40,
        "unit": "mg",
        "elderly_note": "与氨氯地平台用时不超过 20mg/日。",
    },
    "地西泮": {
        "common_dose": "2-5mg/次，睡前服用",
        "max_daily_dose": 10,
        "unit": "mg",
        "elderly_note": "老年人半衰期显著延长，应尽量避免长期使用，跌倒风险高。",
    },
    "佐匹克隆": {
        "common_dose": "3.75mg/次，睡前服用",
        "max_daily_dose": 7.5,
        "unit": "mg",
        "elderly_note": "老年人起始 3.75mg，短期使用（不超过 4 周）。",
    },
    "布洛芬": {
        "common_dose": "200-400mg/次，每8小时1次",
        "max_daily_dose": 1200,
        "unit": "mg",
        "elderly_note": "老年人消化道出血、肾损伤风险高，尽量短程使用。",
    },
    "对乙酰氨基酚": {
        "common_dose": "500mg/次，每6小时1次",
        "max_daily_dose": 2000,
        "unit": "mg",
        "elderly_note": "老年人优先选用的镇痛药，但每日不超过 2g（OTC），注意肝功能。",
    },
    "氯吡格雷": {
        "common_dose": "75mg/次，每日1次",
        "max_daily_dose": 75,
        "unit": "mg",
        "elderly_note": "负荷剂量 300mg 仅在 ACS/支架术后使用。",
    },
    "奥美拉唑": {
        "common_dose": "20mg/次，每日1次",
        "max_daily_dose": 40,
        "unit": "mg",
        "elderly_note": "长期使用注意骨折风险和 B12 缺乏。",
    },
    "帕罗西汀": {
        "common_dose": "10-20mg/次，每日1次",
        "max_daily_dose": 20,
        "unit": "mg",
        "elderly_note": "老年人起始 10mg，注意抗胆碱能副作用和低钠血症。",
    },
    "舍曲林": {
        "common_dose": "50-100mg/次，每日1次",
        "max_daily_dose": 150,
        "unit": "mg",
        "elderly_note": "老年人起始 25-50mg，相对安全的 SSRI 选择。",
    },
}

# ── 疾病-药物禁忌矩阵 ────────────────────────────────────
# key = 疾病名, value = { 禁忌药物: 原因 }

_DISEASE_DRUG_CONTRA: Dict[str, dict] = {
    "高血压": {
        "布洛芬": "NSAIDs 可升高血压、减弱降压药效果，高血压患者慎用。",
        "伪麻黄碱": "拟交感神经药可显著升高血压。",
    },
    "糖尿病": {
        "泼尼松": "糖皮质激素可升高血糖，糖尿病患者需密切监测血糖。",
        "氢氯噻嗪": "噻嗪类利尿剂可能影响糖代谢，需监测血糖。",
    },
    "冠心病": {
        "布洛芬": "NSAIDs 增加心血管事件风险，冠心病患者尽量避免长期使用。",
        "曲马多": "老年冠心病患者慎用，有心脏事件风险。",
    },
    "慢性肾病": {
        "二甲双胍": "eGFR<30 禁用，eGFR 30-45 减量，防乳酸酸中毒。",
        "布洛芬": "NSAIDs 可致肾血流减少，肾功能恶化，CKD 患者避免使用。",
        "华法林": "严重肾功能不全时需调整剂量并加强监测。",
    },
    "心力衰竭": {
        "维拉帕米": "非二氢吡啶类 CCB 在心衰患者中一般禁用（抑制心肌收缩力）。",
        "美托洛尔": "心衰稳定期可使用（从小剂量起始），急性失代偿期慎用。",
        "布洛芬": "NSAIDs 导致水钠潴留，加重心衰。",
    },
    "消化性溃疡": {
        "阿司匹林": "阿司匹林损伤胃黏膜，活动性溃疡属禁忌；如需抗血小板应联用 PPI。",
        "布洛芬": "NSAIDs 损伤胃黏膜，溃疡活动期禁用。",
        "华法林": "消化性溃疡合并出血风险高，需评估后使用。",
    },
    "青光眼": {
        "苯海拉明": "第一代抗组胺药有抗胆碱能作用，闭角型青光眼禁用。",
        "地西泮": "苯二氮卓类有轻度抗胆碱能作用，闭角型青光眼慎用。",
        "阿米替林": "TCA 抗胆碱能作用强，闭角型青光眼禁用。",
    },
    "前列腺增生": {
        "苯海拉明": "抗胆碱能作用加重排尿困难，前列腺增生患者慎用。",
        "阿米替林": "抗胆碱能副作用强，前列腺增生患者禁用。",
        "奥昔布宁": "抗胆碱能药加重尿潴留，已有 BPH 的老年人慎用。",
    },
    "帕金森病": {
        "甲氧氯普胺": "多巴胺拮抗剂可加重帕金森症状，禁用。",
        "氟哌啶醇": "典型抗精神病药阻断多巴胺，加重帕金森症状。",
    },
    "慢性阻塞性肺疾病": {
        "美托洛尔": "非选择性 β受体阻滞剂可诱发支气管痉挛；"
                    "选择性 β1 阻滞剂（如比索洛尔）相对安全但需慎用。",
    },
    "肝功能不全": {
        "对乙酰氨基酚": "肝病者每日不超过 2g，严重肝功能不全禁用。",
        "阿托伐他汀": "活动性肝病禁用，既往转氨酶升高 3 倍以上慎用。",
    },
}


# ── DDI 查询辅助函数 ─────────────────────────────────────

def _check_ddi(drugs: List[str]) -> List[dict]:
    """检查药物列表中两两组合的 DDI"""
    alerts = []
    drug_lower = [d.strip().lower() for d in drugs]
    # 同时维护中文原名映射
    drug_map = {}
    for d in drugs:
        drug_map[d.strip().lower()] = d.strip()

    checked = set()
    for i, da_lower in enumerate(drug_lower):
        for j, db_lower in enumerate(drug_lower):
            if i >= j:
                continue
            pair_key = (drug_map[da_lower], drug_map[db_lower])
            rev_key = (pair_key[1], pair_key[0])

            if pair_key in checked or rev_key in checked:
                continue
            checked.add(pair_key)

            info = _DDI_MATRIX.get(pair_key) or _DDI_MATRIX.get(rev_key)
            if info:
                alerts.append({
                    "drug_a": pair_key[0],
                    "drug_b": pair_key[1],
                    "severity": info["severity"],
                    "description": info["description"],
                    "action": info["action"],
                })
    return alerts


def _check_dose(drug_name: str, dose_value: Optional[float] = None) -> Optional[dict]:
    """检查单药剂量是否超出老年人安全范围"""
    ref = _MEDICATION_DOSE_REF.get(drug_name)
    if not ref:
        return None

    result = {
        "drug": drug_name,
        "common_dose": ref["common_dose"],
        "max_daily_dose": ref["max_daily_dose"],
        "unit": ref["unit"],
        "elderly_note": ref["elderly_note"],
    }

    if dose_value is not None and dose_value > ref["max_daily_dose"]:
        result["dose_warning"] = (
            f"⚠️ 剂量异常：{drug_name} 输入日剂量 {dose_value}{ref['unit']}，"
            f"超出老年人推荐最大日剂量 {ref['max_daily_dose']}{ref['unit']}，"
            f"请立即与处方医师确认。"
        )

    return result


def _check_disease_drug(diseases: List[str], drugs: List[str]) -> List[dict]:
    """检查疾病-药物禁忌"""
    alerts = []
    for disease in diseases:
        disease = disease.strip()
        contra = _DISEASE_DRUG_CONTRA.get(disease)
        if not contra:
            continue
        for drug in drugs:
            drug = drug.strip()
            if drug in contra:
                alerts.append({
                    "disease": disease,
                    "drug": drug,
                    "reason": contra[drug],
                })
    return alerts


def _format_medication_result(
    ddi_alerts: List[dict],
    dose_info: List[dict],
    contra_alerts: List[dict],
    drug_list: List[str],
) -> str:
    """格式化输出"""
    lines = []
    lines.append("══════════════════════════════════════")
    lines.append("          老年人用药安全检查报告")
    lines.append("══════════════════════════════════════")
    lines.append(f"检查药物：{'、'.join(drug_list)}")
    lines.append("")

    # DDI 部分
    if ddi_alerts:
        lines.append("【药物-药物相互作用 (DDI)】")
        for i, a in enumerate(ddi_alerts, 1):
            lines.append(f"  {i}. [{a['severity']}] {a['drug_a']} + {a['drug_b']}")
            lines.append(f"     说明：{a['description']}")
            lines.append(f"     建议：{a['action']}")
            lines.append("")
    else:
        lines.append("【药物-药物相互作用 (DDI)】")
        lines.append("  未发现已知的严重药物相互作用。")
        lines.append("")

    # 剂量检查
    if dose_info:
        lines.append("【剂量参考与异常检测】")
        for d in dose_info:
            lines.append(f"  · {d['drug']}")
            lines.append(f"    常用剂量：{d['common_dose']}")
            lines.append(f"    老年人最大日剂量：{d['max_daily_dose']}{d['unit']}")
            lines.append(f"    老年人注意事项：{d['elderly_note']}")
            if "dose_warning" in d:
                lines.append(f"    {d['dose_warning']}")
            lines.append("")
    else:
        lines.append("【剂量参考与异常检测】")
        lines.append("  所查药物暂无内置剂量参考数据，请查阅药品说明书。")
        lines.append("")

    # 疾病-药物禁忌
    if contra_alerts:
        lines.append("【疾病-药物禁忌】")
        for i, c in enumerate(contra_alerts, 1):
            lines.append(f"  {i}. {c['disease']} + {c['drug']}")
            lines.append(f"     原因：{c['reason']}")
            lines.append("")
    else:
        lines.append("【疾病-药物禁忌】")
        lines.append("  未发现当前疾病与所查药物存在禁忌。")
        lines.append("")

    # 紧急信号
    lines.append("【紧急联系方式】")
    lines.append("  · 急救电话：120")
    lines.append("  · 心理援助热线：400-161-9995")
    lines.append("══════════════════════════════════════")

    result = "\n".join(lines)
    result += MEDICAL_DISCLAIMER
    return result


# ── 工具主函数 ───────────────────────────────────────────

def _medication_guide_func(
    drugs: str,
    diseases: str = "",
    doses: str = "",
) -> str:
    """
    老年人用药安全检查。
    drugs: 药物名称列表（逗号分隔），如 "华法林,阿司匹林"
    diseases: 患者疾病列表（逗号分隔），如 "高血压,糖尿病"（可选）
    doses: 药物日剂量列表（逗号分隔，数字），如 "5,100"（可选，与 drugs 顺序对应）
    """
    drug_list = [d.strip() for d in drugs.split(",") if d.strip()]
    if not drug_list:
        return "请提供至少一种药物名称。" + MEDICAL_DISCLAIMER

    disease_list = [d.strip() for d in diseases.split(",") if d.strip()] if diseases else []
    dose_list = []
    if doses:
        for d in doses.split(","):
            d = d.strip()
            if d:
                try:
                    dose_list.append(float(d))
                except ValueError:
                    dose_list.append(None)

    # DDI 检查
    ddi_alerts = _check_ddi(drug_list) if len(drug_list) >= 2 else []

    # 剂量检查
    dose_info = []
    for i, drug in enumerate(drug_list):
        dose_val = dose_list[i] if i < len(dose_list) else None
        info = _check_dose(drug, dose_val)
        if info:
            dose_info.append(info)

    # 疾病-药物禁忌
    contra_alerts = _check_disease_drug(disease_list, drug_list) if disease_list else []

    return _format_medication_result(ddi_alerts, dose_info, contra_alerts, drug_list)


# ── Tool 工厂 ───────────────────────────────────────────

def build_medication_tool() -> Tool:
    """构建用药指导工具"""
    return Tool(
        name="medication_guide",
        description=(
            "老年人用药安全检查工具。输入药物名称（逗号分隔），可选输入患者疾病和药物日剂量，"
            "返回药物-药物相互作用(DDI)、剂量异常检测、疾病-药物禁忌检查结果。"
            "所有结果附带医疗免责声明。"
        ),
        func=_medication_guide_func,
        param_descriptions={
            "drugs": {
                "description": "药物通用名列表，逗号分隔，如 '华法林,阿司匹林'",
                "required": True,
            },
            "diseases": {
                "description": "患者疾病列表，逗号分隔，如 '高血压,糖尿病'（可选）",
                "required": False,
            },
            "doses": {
                "description": "药物日剂量数值列表，逗号分隔，如 '5,100'（可选，与药物顺序对应）",
                "required": False,
            },
        },
    )
