"""
tourism_team - 文旅导览 Planner-Executor 团队

功能：
1. Planner 分析用户问题，路由到对应专家
2. 三个 Executor 各有专长：
   - attraction（景点专家）：使用 attraction_guide 工具
   - route（路线专家）：使用 route_planner 工具
   - culture（文化专家）：使用 cultural_story 工具
3. 惰性初始化：不在 import 时创建任何实例

使用方式：
    team = build_tourism_team()
    result = team.run("故宫的开放时间是什么？")
"""
from __future__ import annotations

import logging
from typing import Optional

from base.agent_framework import Agent, PlannerExecutorTeam, Tool
from base.model_factory import ModelFactory
from .tools import (
    create_attraction_guide_tool,
    create_route_planner_tool,
    create_cultural_story_tool,
)

logger = logging.getLogger(__name__)

# ── Executor 系统提示词 ──────────────────────────────────

ATTRACTION_EXECUTOR_PROMPT = """你是景点导览专家，专门为老年游客提供景点信息服务。

你的职责：
1. 使用 attraction_guide 工具查询景点的详细信息
2. 包括开放时间、门票价格、交通指南、主要看点
3. 特别关注老年人优惠政策（60岁以上半价，65岁以上免费等）
4. 提供老人出行温馨提示

服务原则：
- 语言亲切易懂，不用专业术语
- 主动提醒老人优惠政策
- 信息要完整准确，不要遗漏重要内容
- 如果工具没有查到，可以适当用自己的知识补充

使用工具：
- attraction_guide：传入景点名称即可查询

记住：你面对的是中老年用户，耐心和准确最重要。"""


ROUTE_EXECUTOR_PROMPT = """你是旅游路线规划专家，专门为老年游客设计旅游行程。

你的职责：
1. 使用 route_planner 工具规划多日行程
2. 行程要考虑老人的体力和节奏（不要太赶）
3. 包含上午、下午、晚间分段安排
4. 提供交通方式和老人出行建议

服务原则：
- 行程安排要宽松，每天2个景点为宜
- 必须包含午休时间
- 主动提醒老人出行注意事项
- 如果工具不支持该城市，给出通用建议

使用工具：
- route_planner：传入城市名、天数、特别想去的景点

记住：老年人的旅行应该慢节奏、重安全、求舒适。"""


CULTURE_EXECUTOR_PROMPT = """你是文化故事讲述专家，专门为老年游客讲解景点背后的文化故事。

你的职责：
1. 使用 cultural_story 工具查询景点的文化故事
2. 按主题分类讲述：历史、建筑、传说、人物
3. 语言生动有趣，让老人听得津津有味
4. 如果用户没有指定主题，讲述全部主题

服务原则：
- 故事要讲得通俗有趣，不枯燥
- 可以适当加入自己的知识补充
- 避免过于学术化的表述
- 让老人在游览前对景点有充分了解

使用工具：
- cultural_story：传入景点名称和可选的主题

记住：好的故事让旅行更有意义，你是旅行的文化向导。"""


PLANNER_PROMPT = """你是一个智能调度器。根据用户的问题，选择最合适的文旅专家来回答。

可选择的专家及其职责：
{executor_descriptions}

选择原则：
1. 用户询问景点信息（开放时间、门票、交通、看点）→ 选择"attraction"
2. 用户询问行程规划、旅游路线、怎么安排几天游玩 → 选择"route"
3. 用户询问景点故事、历史背景、文化典故、传说 → 选择"culture"
4. 用户的问题涉及多个方面，选择最主要的一个
5. 如果无法判断，选择"attraction"（景点导览是默认服务）

请返回 JSON 格式：{{"executor": "专家名称", "reason": "选择原因"}}
只返回 JSON，不要附加其他内容。"""


# ── 团队构建 ────────────────────────────────────────────

# 缓存（惰性初始化）
_team: Optional[PlannerExecutorTeam] = None


def _build_executors(llm) -> dict[str, Agent]:
    """构建三个专家 Executor"""
    attraction_agent = Agent(
        llm=llm,
        system_prompt=ATTRACTION_EXECUTOR_PROMPT,
        tools=[create_attraction_guide_tool()],
        name="景点导览专家",
        max_iterations=5,
    )

    route_agent = Agent(
        llm=llm,
        system_prompt=ROUTE_EXECUTOR_PROMPT,
        tools=[create_route_planner_tool()],
        name="路线规划专家",
        max_iterations=5,
    )

    culture_agent = Agent(
        llm=llm,
        system_prompt=CULTURE_EXECUTOR_PROMPT,
        tools=[create_cultural_story_tool()],
        name="文化故事专家",
        max_iterations=5,
    )

    return {
        "attraction": attraction_agent,
        "route": route_agent,
        "culture": culture_agent,
    }


def build_tourism_team(
    llm=None,
    verbose: bool = False,
) -> PlannerExecutorTeam:
    """
    构建 Planner-Executor 文旅导览团队

    Args:
        llm: LLM 实例（如未提供则从 ModelFactory 获取）
        verbose: 是否输出详细日志（包括 Planner 路由信息）

    Returns:
        PlannerExecutorTeam 实例
    """
    global _team
    if _team is not None and not verbose:
        return _team

    if llm is None:
        llm = ModelFactory.get_llm()

    executors = _build_executors(llm)

    _team = PlannerExecutorTeam(
        llm=llm,
        executors=executors,
        planner_prompt=PLANNER_PROMPT,
        verbose=verbose,
    )

    logger.info(
        "文旅导览团队已构建（executors=%s）" % list(executors.keys())
    )
    return _team


def _reset_team():
    """重置团队缓存（用于测试或配置变更后刷新）"""
    global _team
    _team = None


# ── 便捷封装 ────────────────────────────────────────────

class TourismTeam:
    """
    文旅导览团队便捷封装

    用法：
        team = TourismTeam()
        result = team.chat("帮我查一下故宫的门票信息")
        result = team.chat("规划一个北京两日游")
    """

    def __init__(self, llm=None, verbose: bool = False):
        self._team = build_tourism_team(llm=llm, verbose=verbose)
        self._chat_history: list = []

    def chat(self, query: str) -> str:
        """与团队对话"""
        result = self._team.run(query, chat_history=self._chat_history)
        # 保存对话历史
        self._chat_history.append(("human", query))
        self._chat_history.append(("ai", result))
        # 保留最近10轮对话
        if len(self._chat_history) > 20:
            self._chat_history = self._chat_history[-20:]
        return result

    def reset(self):
        """清空对话历史"""
        self._chat_history.clear()

    def run(self, query: str) -> str:
        """直接执行查询（不保存对话历史）"""
        return self._team.run(query)
