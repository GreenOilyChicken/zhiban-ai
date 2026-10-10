"""
elderly_team — 银发康养 Planner-Executor 团队构建器

4 个 Executor 专家：
1. medication:  用药安全专家（DDI、剂量、禁忌）
2. care:        护理顾问（慢病护理、心理健康）
3. rehab:       康复训练师（术后分阶段康复）
4. ltc:         长护险顾问（政策咨询、申请指导）

Planner 根据用户问题自动路由到最合适的专家。
惰性初始化：不在模块级别创建实例。
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

from base.agent_framework import Agent, PlannerExecutorTeam, Tool
from base.model_factory import ModelFactory

from .tools.medication_guide import build_medication_tool
from .tools.care_advice import build_care_advice_tool
from .tools.rehab_plan import build_rehab_plan_tool
from .tools.long_term_care import build_long_term_care_tool

logger = logging.getLogger(__name__)

# ── 各 Executor 的系统提示词 ─────────────────────────────

_MEDICATION_PROMPT = """\
你是「银发康养·用药安全专家」，专注于老年人用药安全。
你的职责：
1. 使用 medication_guide 工具查询药物-药物相互作用(DDI)、剂量异常、疾病-药物禁忌
2. 解释药物相互作用的风险和机制
3. 给出用药安全建议（但不替代医师处方）
4. 对多重用药（≥5种）的老年人提出"药物重整"建议
5. 始终提醒用户：所有用药信息仅供参考，不替代执业医师面诊

紧急信号：
- 急救电话 120：适用于药物严重不良反应（过敏性休克、严重出血等）
- 心理援助热线 400-161-9995
"""

_CARE_PROMPT = """\
你是「银发康养·护理顾问」，专注于老年人慢病护理和心理健康。
你的职责：
1. 使用 care_advice 工具获取基于知识库的护理建议
2. 提供高血压、糖尿病、冠心病、脑卒中、骨质疏松等慢病的日常护理指导
3. 关注老年人心理健康（抑郁、焦虑的识别和关怀）
4. 给出饮食、运动、监测、用药遵从的个性化建议
5. 提醒家属护理要点和急症信号

紧急信号：
- 急救电话 120：适用于胸痛、卒中(FAST)、严重呼吸困难、意识改变
- 心理援助热线 400-161-9995：适用于自伤自杀念头、严重抑郁
"""

_REHAB_PROMPT = """\
你是「银发康养·康复训练师」，专注于老年人术后康复指导。
你的职责：
1. 使用 rehab_plan 工具查询术后分阶段康复计划
2. 覆盖：髋关节置换、膝关节置换、心脏支架植入、脊柱手术
3. 详细解释每个阶段的训练目标、训练项目、注意事项
4. 根据患者年龄、合并症情况给出个性化调整建议
5. 强调康复安全：防跌倒、防脱位、防并发症

紧急信号：
- 急救电话 120：训练中如出现剧烈疼痛、关节弹响、胸闷气短
- 心理援助热线 400-161-9995
"""

_LTC_PROMPT = """\
你是「银发康养·长护险顾问」，专注于长期护理保险政策咨询和申请指导。
你的职责：
1. 使用 long_term_care 工具模拟长护险申请提交（身份验证、脱敏处理）
2. 解答长护险参保条件、失能等级、待遇标准、申请流程等政策问题
3. 指导家属准备申请材料
4. 身份证号和手机号在输出中始终脱敏
5. 提醒用户此为模拟申请，正式申请需前往当地医保经办机构

紧急信号：
- 医保服务热线 12393：长护险政策咨询
- 心理援助热线 400-161-9995
"""

# ── Planner 提示词 ───────────────────────────────────────

_PLANNER_PROMPT = """\
你是一个调度器。根据用户问题，选择最合适的专家来回答。
可选择的专家及其职责：
{executor_descriptions}

选择规则：
- 用药、药物相互作用、剂量、药物禁忌 → medication
- 慢病护理、饮食运动、心理健康、日常照护 → care
- 术后康复、康复训练、关节置换、心脏支架术后 → rehab
- 长护险、长期护理保险、失能评估、照护申请 → ltc
- 涉及多个领域时，选择最核心的领域

请返回 JSON 格式：{{"executor": "专家名称", "reason": "选择原因"}}
只返回 JSON，不要附加其他内容。
"""

# ── 惰性缓存 ───────────────────────────────────────────

_elderly_team: Optional[PlannerExecutorTeam] = None


def build_elderly_team(
    max_iterations: int = 10,
    verbose: bool = False,
) -> PlannerExecutorTeam:
    """
    构建银发康养 Planner-Executor 团队（4 个专家 Executor + 1 个 Planner）
    惰性初始化：首次调用创建实例，后续返回缓存。
    """
    global _elderly_team
    if _elderly_team is not None:
        return _elderly_team

    llm = ModelFactory.get_llm()

    # 构建 4 个 Executor Agent
    # 每个 Executor 配备自己领域的工具
    executors: Dict[str, Agent] = {
        "medication": Agent(
            llm=llm,
            system_prompt=_MEDICATION_PROMPT,
            tools=[build_medication_tool()],
            name="用药安全专家",
            max_iterations=max_iterations,
            verbose=verbose,
        ),
        "care": Agent(
            llm=llm,
            system_prompt=_CARE_PROMPT,
            tools=[build_care_advice_tool()],
            name="护理顾问",
            max_iterations=max_iterations,
            verbose=verbose,
        ),
        "rehab": Agent(
            llm=llm,
            system_prompt=_REHAB_PROMPT,
            tools=[build_rehab_plan_tool()],
            name="康复训练师",
            max_iterations=max_iterations,
            verbose=verbose,
        ),
        "ltc": Agent(
            llm=llm,
            system_prompt=_LTC_PROMPT,
            tools=[build_long_term_care_tool()],
            name="长护险顾问",
            max_iterations=max_iterations,
            verbose=verbose,
        ),
    }

    _elderly_team = PlannerExecutorTeam(
        llm=llm,
        executors=executors,
        planner_prompt=_PLANNER_PROMPT,
        verbose=verbose,
    )

    logger.info(
        f"银发康养 Team 已构建: executors={list(executors.keys())}, "
        f"max_iterations={max_iterations}"
    )
    return _elderly_team


def reset_elderly_team():
    """重置缓存（用于测试或配置变更后重建）"""
    global _elderly_team
    _elderly_team = None
    logger.info("银发康养 Team 缓存已重置")
