"""
government_team — 政务政策 Planner-Executor 团队
使用 PlannerExecutorTeam 模式，Planner 将用户问题路由到三个专项执行器：

1. **policy_executor**（政策专家）：负责政策内容解读、政策背景分析
2. **regulation_executor**（法规专家）：负责法规条文解释、合规判断
3. **procedure_executor**（办事流程专家）：负责办事流程、申报指南

每个 executor 都挂载 search_policy_db 工具，但使用不同的系统提示词。
"""
from __future__ import annotations

import logging
from typing import Dict

from base.agent_framework import Agent, PlannerExecutorTeam
from base.model_factory import ModelFactory

from .government_agent import GOVERNMENT_AGENT_TOOLS

logger = logging.getLogger(__name__)


# ── 各执行器系统提示词 ────────────────────────────────

POLICY_EXECUTOR_PROMPT = """\
你是一名政务政策解读专家。你的核心职责是：

1. 使用 search_policy_db 工具检索政策知识库中的政策文件。
2. 对政策内容进行准确解读，包括政策背景、目标、适用范围、核心条款。
3. 分析政策对不同群体（企业、个人、基层单位）的影响。
4. 对比新旧政策的变化，指出关键差异。

**回答规范：**
- 先检索知识库，再基于检索结果回答。
- 明确标注信息来源（文件名）。
- 如知识库中无相关内容，如实告知，不编造政策内容。
- 用通俗易懂的语言解释政策术语，必要时举例说明。
"""

REGULATION_EXECUTOR_PROMPT = """\
你是一名政务法规条文专家。你的核心职责是：

1. 使用 search_policy_db 工具检索法规条文和规范性文件。
2. 对法规条文进行准确解释，包括适用条件、法律后果、例外情况。
3. 判断特定行为或情况是否符合法规要求（合规判断）。
4. 引用具体条文编号，确保可追溯。

**回答规范：**
- 引用法规时标明法规名称和具体条款编号。
- 对法规解释保持审慎，区分强制性规定与指导性规定。
- 如涉及法律风险，建议用户咨询专业法律人士。
- 如知识库中无相关法规，如实告知，不编造条文。
"""

PROCEDURE_EXECUTOR_PROMPT = """\
你是一名政务办事流程咨询专家。你的核心职责是：

1. 使用 search_policy_db 工具检索办事指南、流程文件。
2. 清晰说明办事流程：所需材料、办理步骤、办理时限、收费标准。
3. 指明办事地点、窗口、线上渠道。
4. 提醒注意事项和常见问题。

**回答规范：**
- 按步骤说明流程，使用编号列表。
- 列明所需材料清单，标注原件/复印件要求。
- 如有线上办理渠道，提供相关指引。
- 如知识库中无相关流程信息，如实告知，建议咨询相关部门。
"""


# ── Planner 提示词 ────────────────────────────────────

GOVERNMENT_PLANNER_PROMPT = """\
你是一个政务问题调度器。根据用户问题的类型，选择最合适的专家来回答。

可选专家及其职责：
{executor_descriptions}

选择规则：
- 涉及政策解读、政策背景、政策影响分析 → 选择 "policy"
- 涉及法规条文、合规判断、法律解释 → 选择 "regulation"
- 涉及办事流程、申报指南、材料清单 → 选择 "procedure"
- 涉及培训台账生成 → 选择 "policy"（台账工具在所有专家中都可用）
- 综合性问题 → 选择最相关的专家

请返回 JSON 格式：{{"executor": "专家名称", "reason": "选择原因"}}
只返回 JSON，不要附加其他内容。
"""


# ── 团队构建 ──────────────────────────────────────────

def build_government_team(verbose: bool = False) -> PlannerExecutorTeam:
    """
    构建政务政策 Planner-Executor 团队（惰性，不在模块级实例化）。

    Args:
        verbose: 是否输出详细日志
    Returns:
        配置好的 PlannerExecutorTeam 实例
    """
    llm = ModelFactory.get_llm()
    tools = list(GOVERNMENT_AGENT_TOOLS)

    # 三个专项执行器
    policy_executor = Agent(
        llm=llm,
        system_prompt=POLICY_EXECUTOR_PROMPT,
        tools=tools,
        name="政策解读专家",
        max_iterations=10,
        verbose=verbose,
    )

    regulation_executor = Agent(
        llm=llm,
        system_prompt=REGULATION_EXECUTOR_PROMPT,
        tools=tools,
        name="法规条文专家",
        max_iterations=10,
        verbose=verbose,
    )

    procedure_executor = Agent(
        llm=llm,
        system_prompt=PROCEDURE_EXECUTOR_PROMPT,
        tools=tools,
        name="办事流程专家",
        max_iterations=10,
        verbose=verbose,
    )

    executors: Dict[str, Agent] = {
        "policy": policy_executor,
        "regulation": regulation_executor,
        "procedure": procedure_executor,
    }

    team = PlannerExecutorTeam(
        llm=llm,
        executors=executors,
        planner_prompt=GOVERNMENT_PLANNER_PROMPT,
        verbose=verbose,
    )

    logger.info("政务政策团队已构建: policy / regulation / procedure")
    return team
