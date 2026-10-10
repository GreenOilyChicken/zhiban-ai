"""
care_advice — 老年人护理建议工具

功能：
1. 优先通过 ChromaDB 向量知识库检索护理建议（RAG）
2. 如果知识库不可用或检索结果不足，回退到内置 _FALLBACK_KB
3. 线程安全的向量数据库访问（threading.Lock）

覆盖范围：
- 高血压、糖尿病、冠心病、脑卒中、骨质疏松
- 老年抑郁/焦虑
"""
from __future__ import annotations

import logging
import os
import re
import threading
from typing import Dict, List, Optional

from base.agent_framework import Tool

logger = logging.getLogger(__name__)

# ── 线程锁：保护向量数据库访问 ───────────────────────────

_vectordb_lock = threading.Lock()

# ── 内置回退知识库 ───────────────────────────────────────
# 当 ChromaDB 不可用或检索结果不足时使用

_FALLBACK_KB: Dict[str, dict] = {
    "高血压": {
        "aliases": ["高血压", "血压高", "高血压病", "hypertension"],
        "summary": "老年人高血压管理：目标血压 <150/90 mmHg（80岁以上可适当放宽），控制盐摄入 <5g/日。",
        "advice": [
            "【饮食】低盐低脂饮食，每日食盐不超过 5 克（约一啤酒瓶盖），多吃新鲜蔬果、全谷物。",
            "【运动】中等强度有氧运动（如快走、太极拳），每周 5 次以上，每次 30 分钟。避免剧烈运动。",
            "【监测】建议家庭自测血压，每日早晚各测 1 次，每次测 2-3 遍取平均值。记录血压日记。",
            "【用药】遵医嘱按时服药，不可自行停药或调量。即使血压正常也需要继续服药。",
            "【注意】体位性低血压风险：起床、起立时动作要慢，先坐 1 分钟再站。",
            "【急症信号】如出现剧烈头痛、视物模糊、胸痛、肢体麻木无力，立即拨打 120。",
        ],
    },
    "糖尿病": {
        "aliases": ["糖尿病", "血糖高", "高血糖", "diabetes", "2型糖尿病"],
        "summary": "老年人糖尿病管理：空腹血糖目标 7-9 mmol/L（根据并发症放宽），HbA1c 目标 7-8%。",
        "advice": [
            "【饮食】定时定量进餐，控制总热量。主食粗细搭配，减少精制糖。少食多餐。",
            "【运动】餐后 1 小时散步 30 分钟，避免空腹运动防低血糖。每周至少 150 分钟中等强度运动。",
            "【监测】定期监测空腹和餐后 2 小时血糖。每 3 个月查 HbA1c。",
            "【足部护理】每日检查足部皮肤，温水洗脚（水温不超 37°C），穿舒适合脚的鞋袜，避免赤脚行走。",
            "【用药】口服降糖药按时服用，胰岛素注射需轮换注射部位。不可自行停药。",
            "【低血糖】随身携带糖果或饼干。如出现心慌、出汗、手抖，立即进食 15g 糖。",
            "【急症信号】意识改变、严重低血糖（血糖<3.9mmol/L）不缓解，立即送医。",
        ],
    },
    "冠心病": {
        "aliases": ["冠心病", "心绞痛", "心肌缺血", "冠状动脉粥样硬化", "coronary heart disease", "CHD"],
        "summary": "老年人冠心病管理：控制危险因素（血压、血脂、血糖），规律服药，识别心绞痛和心梗征兆。",
        "advice": [
            "【饮食】低盐低脂饮食，限制饱和脂肪和反式脂肪。多吃鱼类、蔬果、全谷物。",
            "【运动】适度有氧运动，避免剧烈活动和情绪激动。如出现胸痛立即停止。",
            "【用药】阿司匹林/氯吡格雷（抗血小板）、他汀（降脂）、β受体阻滞剂等需长期规律服用。",
            "【硝酸甘油】随身携带硝酸甘油喷雾或片剂。心绞痛发作时舌下含服，1-2 分钟缓解。",
            "【诱因避免】避免寒冷刺激、饱餐、剧烈运动、情绪激动。冬季注意保暖。",
            "【急症信号】胸痛持续 >15 分钟、含服硝酸甘油不缓解、伴大汗/恶心/呼吸困难，"
            "可能为急性心梗，立即拨打 120，原地平卧休息，勿自行前往医院。",
        ],
    },
    "脑卒中": {
        "aliases": ["脑卒中", "中风", "脑梗", "脑出血", "stroke", "脑血管意外"],
        "summary": "脑卒中后护理：康复训练越早越好，预防复发（抗血小板/抗凝），预防并发症（压疮、感染、深静脉血栓）。",
        "advice": [
            "【康复训练】病情稳定后 24-48 小时即应开始康复。包括肢体被动/主动运动、言语训练、吞咽训练。",
            "【体位管理】每 2 小时翻身一次防压疮。偏瘫侧肢体注意良肢位摆放。",
            "【吞咽护理】如有吞咽困难，进食时坐起 90°，食物做成糊状或半流质，避免饮水呛咳（可用增稠剂）。",
            "【用药】二级预防：抗血小板（阿司匹林/氯吡格雷）或抗凝（房颤患者），降压降脂达标。",
            "【预防跌倒】偏瘫患者平衡功能下降，需使用助行器，卫生间安装扶手，地面防滑。",
            "【情绪管理】卒中后抑郁发生率高达 30-50%，关注患者情绪，必要时就医。",
            "【急症信号】FAST 识别——Face 面部不对称、Arm 手臂无力、Speech 言语不清、Time 立即拨打 120。",
        ],
    },
    "骨质疏松": {
        "aliases": ["骨质疏松", "骨密度低", "osteoporosis"],
        "summary": "老年人骨质疏松管理：补充钙和维生素 D，防跌倒，必要时使用双膦酸盐等抗骨松药物。",
        "advice": [
            "【营养】每日钙摄入 1000-1200mg（饮食+补充剂），维生素 D 800-1000IU/日。",
            "【运动】负重运动（如散步、太极拳）和抗阻训练，每周 3-5 次。改善平衡防跌倒。",
            "【日照】每日户外日照 15-30 分钟（上午 10 点前或下午 3 点后），促进维生素 D 合成。",
            "【防跌倒】清除地面障碍物，卫生间装扶手和防滑垫，夜间留小夜灯。穿防滑鞋。",
            "【用药】遵医嘱使用双膦酸盐（如阿仑膦酸钠，需空腹服用、保持直立 30 分钟）"
            "或地舒单抗。不可自行停药。",
            "【检查】建议每年查一次骨密度（DEXA）。如身高变矮 >3cm 或驼背加重，警惕椎体压缩骨折。",
        ],
    },
    "老年抑郁": {
        "aliases": ["老年抑郁", "抑郁症", "情绪低落", "抑郁", "depression"],
        "summary": "老年抑郁症：常表现为躯体症状（疼痛、失眠、乏力）而非情绪表达，易被漏诊。及时治疗预后良好。",
        "advice": [
            "【识别信号】持续 2 周以上的情绪低落、兴趣减退、失眠或嗜睡、食欲下降、"
            "自责自罪、反复提及死亡——需高度警惕。",
            "【陪伴沟通】耐心倾听，不要说'想开点''别矫情'。表达理解和支持，鼓励就诊。",
            "【运动日照】每日户外活动 30 分钟以上，阳光和运动对改善情绪有循证依据。",
            "【社交支持】鼓励参加社区活动、老年大学、兴趣小组，减少独处。",
            "【用药】抗抑郁药（如舍曲林、艾司西酞普兰）起效需 2-4 周，需坚持服药，"
            "不可自行停药。老年人起始剂量减半。",
            "【急症信号】如有自伤、自杀念头或行为，这是医疗急症！"
            "请立即拨打心理援助热线 400-161-9995，或拨打 120，不要让患者独处。",
        ],
    },
    "老年焦虑": {
        "aliases": ["老年焦虑", "焦虑症", "焦虑", "anxiety", "紧张"],
        "summary": "老年焦虑症：表现为过度担心、坐立不安、心慌、失眠，常与躯体疾病共病。需排除甲亢、心脏病等器质性原因。",
        "advice": [
            "【识别信号】持续过度担忧（6 个月以上）、肌肉紧张、心慌、出汗、失眠、"
            "回避社交——需评估焦虑程度。",
            "【放松技巧】腹式呼吸（吸 4 秒、屏 4 秒、呼 6 秒）、渐进性肌肉放松、"
            "正念冥想，每日 2 次。",
            "【运动】规律有氧运动（散步、太极拳）可显著降低焦虑水平。",
            "【睡眠管理】固定作息时间，避免午睡超过 30 分钟，睡前不看手机/电视。",
            "【用药】SSRI（如舍曲林）为一线药物，起效 2-4 周。短期可联用低剂量苯二氮卓类（不超过 2-4 周）。",
            "【急症信号】如焦虑伴惊恐发作（心慌濒死感、呼吸困难），需排除心脏急症；"
            "如有自杀念头，拨打 400-161-9995 心理援助热线。",
        ],
    },
}

# ── 构建 disease 到 key 的索引 ───────────────────────────

_DISEASE_INDEX: Dict[str, str] = {}
for _key, _val in _FALLBACK_KB.items():
    for _alias in _val.get("aliases", []):
        _DISEASE_INDEX[_alias.lower()] = _key


def _match_fallback(query: str) -> Optional[dict]:
    """从内置回退知识库匹配"""
    query_lower = query.lower()
    for alias, key in _DISEASE_INDEX.items():
        if alias in query_lower:
            return _FALLBACK_KB[key]
    return None


def _query_rag(query: str, top_k: int = 5) -> List[str]:
    """
    通过 ChromaDB 向量知识库检索（RAG）
    线程安全：使用 threading.Lock 保护
    """
    results = []
    try:
        with _vectordb_lock:
            from knowledge_base.build_kb import query_knowledge_base
            import config

            docs = query_knowledge_base(
                query=query,
                chroma_dir=config.KB_ELDERLY_DIR / "chroma_db",
                collection_name="elderly_care",
                top_k=top_k,
            )
            for doc in docs:
                content = doc.page_content.strip()
                if content:
                    results.append(content)
    except ImportError:
        logger.warning("knowledge_base 模块不可用，回退到内置知识库")
    except Exception as e:
        logger.warning(f"RAG 检索失败，回退到内置知识库: {e}")

    return results


def _format_care_result(query: str, rag_docs: List[str], fallback: Optional[dict]) -> str:
    """格式化护理建议输出"""
    lines = []
    lines.append("══════════════════════════════════════")
    lines.append("          老年人护理建议")
    lines.append("══════════════════════════════════════")
    lines.append(f"查询：{query}")
    lines.append("")

    # RAG 检索结果
    if rag_docs:
        lines.append("【知识库检索结果】")
        for i, doc in enumerate(rag_docs[:3], 1):
            # 截取前 200 字避免过长
            snippet = doc[:200] + ("..." if len(doc) > 200 else "")
            lines.append(f"  {i}. {snippet}")
            lines.append("")

    # 回退知识库
    if fallback:
        lines.append(f"【{fallback['summary']}】")
        lines.append("")
        for advice in fallback["advice"]:
            lines.append(f"  {advice}")
        lines.append("")

    if not rag_docs and not fallback:
        lines.append("未找到与您查询直接匹配的护理建议。")
        lines.append("建议描述具体疾病名称（如高血压、糖尿病、脑卒中等）以获取更精准的建议。")
        lines.append("")

    # 紧急信号
    lines.append("【紧急联系方式】")
    lines.append("  · 急救电话：120")
    lines.append("  · 心理援助热线：400-161-9995")
    lines.append("══════════════════════════════════════")
    lines.append("")
    lines.append("⚠️ 以上护理建议仅供参考，具体方案请遵医嘱。如有病情变化请及时就诊。")

    return "\n".join(lines)


# ── 工具主函数 ───────────────────────────────────────────

def _care_advice_func(query: str) -> str:
    """
    老年人护理建议查询。
    query: 护理问题或疾病名称，如 "高血压患者饮食注意事项" 或 "脑卒中后康复护理"
    """
    query = query.strip()
    if not query:
        return "请描述您的护理问题或疾病名称。"

    if len(query) > 500:
        logger.warning(f"护理查询过长({len(query)}字符)，截断至500字符")
        query = query[:500]

    # 1. 尝试 RAG 检索
    rag_docs = _query_rag(query, top_k=5)

    # 2. 回退到内置知识库匹配
    fallback = _match_fallback(query)

    # 如果 RAG 有结果但无回退匹配，仍返回 RAG 结果
    # 如果两者都无，返回通用提示
    if not rag_docs and not fallback:
        return (
            "══════════════════════════════════════\n"
            "          老年人护理建议\n"
            "══════════════════════════════════════\n"
            f"查询：{query}\n\n"
            "未找到与您查询直接匹配的护理建议。\n"
            "建议描述具体疾病名称（如高血压、糖尿病、冠心病、脑卒中、骨质疏松、"
            "老年抑郁/焦虑等）以获取更精准的建议。\n\n"
            "【紧急联系方式】\n"
            "  · 急救电话：120\n"
            "  · 心理援助热线：400-161-9995\n"
            "══════════════════════════════════════\n\n"
            "⚠️ 以上护理建议仅供参考，具体方案请遵医嘱。如有病情变化请及时就诊。"
        )

    return _format_care_result(query, rag_docs, fallback)


# ── Tool 工厂 ───────────────────────────────────────────

def build_care_advice_tool() -> Tool:
    """构建护理建议工具"""
    return Tool(
        name="care_advice",
        description=(
            "老年人护理建议查询工具。输入疾病名称或护理问题，"
            "返回基于知识库的护理建议。"
            "覆盖范围：高血压、糖尿病、冠心病、脑卒中、骨质疏松、老年抑郁/焦虑。"
        ),
        func=_care_advice_func,
        param_descriptions={
            "query": {
                "description": "护理问题或疾病名称，如 '高血压患者饮食注意事项' 或 '脑卒中后康复护理'",
                "required": True,
            },
        },
    )
