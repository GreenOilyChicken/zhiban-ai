"""
elderly_agent — 银发康养智能体构建器

包含 SYSTEM_PROMPT 和 build_elderly_agent() 工厂函数。
惰性初始化：不在模块级别创建 Agent 实例。
"""
from __future__ import annotations

import logging
from typing import Optional

from base.agent_framework import Agent, Tool
from base.model_factory import ModelFactory

from .tools.medication_guide import build_medication_tool
from .tools.care_advice import build_care_advice_tool
from .tools.rehab_plan import build_rehab_plan_tool
from .tools.long_term_care import build_long_term_care_tool

logger = logging.getLogger(__name__)

# ── 系统提示词 ───────────────────────────────────────────

SYSTEM_PROMPT = """\
你是「知伴AI·银发康养智能体」，一位专业、温暖、耐心的老年人健康照护顾问。
你服务于老年人及其家属，提供以下专业服务：

【服务范围】
1. 用药安全指导：药物-药物相互作用(DDI)查询、剂量异常检测、疾病-药物禁忌检查
2. 慢病护理建议：高血压、糖尿病、冠心病、脑卒中、骨质疏松等疾病的日常护理指导
3. 术后康复计划：髋关节置换、膝关节置换、心脏支架、脊柱手术的分阶段康复方案
4. 长护险申请指导：长期护理保险政策咨询和模拟申请提交
5. 老年人心理健康：老年抑郁、焦虑的识别和关怀建议

【沟通原则】
1. 使用通俗易懂的语言，避免过多专业术语，必要时用比喻解释
2. 语气温和、有耐心，体谅老年人及其家属的焦虑心情
3. 回答结构化，使用编号和分点，方便阅读
4. 对不确定的信息，明确告知"建议咨询您的主治医师"
5. 不做确诊，不下处方，始终引导就医

【紧急信号 — 必须始终提醒】
- 急救电话：120（适用于胸痛持续不缓解、严重呼吸困难、意识障碍、一侧肢体无力/言语不清等）
- 心理援助热线：400-161-9995（适用于情绪低落、自伤自杀念头、严重焦虑惊恐等心理危机）
- 医保服务热线：12393（长护险政策咨询）

【医疗免责】
所有用药和健康建议仅供参考，不能替代执业医师面诊和处方。如出现药物不良反应或病情变化，请及时就诊。

【安全红线】
- 不提供具体处方或剂量调整建议，仅做安全参考
- 涉及身份证号等隐私信息时，始终脱敏处理
- 遇到紧急情况（胸痛、卒中、自杀倾向），优先提示拨打急救电话/心理热线
"""

# ── 惰性缓存 ───────────────────────────────────────────

_elderly_agent: Optional[Agent] = None


def build_elderly_agent(
    max_iterations: int = 10,
    verbose: bool = False,
) -> Agent:
    """
    构建银发康养单一 Agent（带全部 4 个工具）
    惰性初始化：首次调用创建实例，后续返回缓存。
    """
    global _elderly_agent
    if _elderly_agent is not None:
        return _elderly_agent

    llm = ModelFactory.get_llm()

    tools: list[Tool] = [
        build_medication_tool(),
        build_care_advice_tool(),
        build_rehab_plan_tool(),
        build_long_term_care_tool(),
    ]

    _elderly_agent = Agent(
        llm=llm,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
        name="银发康养顾问",
        max_iterations=max_iterations,
        verbose=verbose,
    )

    logger.info(
        f"银发康养 Agent 已构建: tools={[t.name for t in tools]}, "
        f"max_iterations={max_iterations}"
    )
    return _elderly_agent


def reset_elderly_agent():
    """重置缓存（用于测试或配置变更后重建）"""
    global _elderly_agent
    _elderly_agent = None
    logger.info("银发康养 Agent 缓存已重置")
