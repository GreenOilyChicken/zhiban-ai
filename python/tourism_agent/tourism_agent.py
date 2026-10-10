"""
tourism_agent - 文旅智能导览主智能体

功能：
1. 构建单一智能体，集成景点导览、路线规划、文化故事三个工具
2. 惰性初始化：不在 import 时创建 LLM 或 Agent 实例
3. 适老化的系统提示词

使用方式：
    agent = build_tourism_agent()
    result = agent.run("故宫有什么看点？")
"""
from __future__ import annotations

import logging
from typing import Optional

from base.agent_framework import Agent, Tool
from base.model_factory import ModelFactory
from .tools import (
    create_attraction_guide_tool,
    create_route_planner_tool,
    create_cultural_story_tool,
)

logger = logging.getLogger(__name__)

# ── 系统提示词 ───────────────────────────────────────────

TOURISM_SYSTEM_PROMPT = """你是一位经验丰富、热心周到的文旅导览助手，专门为中老年游客提供旅游信息服务。

你的职责：
1. 帮助用户了解中国各地景点的详细信息（开放时间、门票、交通等）
2. 根据用户需求规划合理的旅游行程
3. 讲述景点背后的文化故事和历史典故

服务原则：
- 语言亲切易懂，不用专业术语和网络用语
- 主动提供实用建议，如老人优惠政策、出行注意事项
- 回答要完整详细，让用户一看就明白
- 如果工具返回的信息不够，可以适当补充你的知识
- 始终关注老年人的出行需求（休息、安全、舒适）

可使用的工具：
1. attraction_guide：查询景点详细信息（开放时间、门票、交通、看点）
2. route_planner：规划多日行程（支持1-3天，按上下午晚间分段）
3. cultural_story：讲述景点文化故事（历史、建筑、传说、人物）

使用工具时注意：
- 用户问景点信息时，先用 attraction_guide 查询
- 用户问行程规划时，先用 route_planner 规划
- 用户问景点故事时，先用 cultural_story 查询
- 工具返回结果后，可以用你的话进行整理和补充
- 如果用户的请求不明确，可以友善地追问

记住：你面对的是中老年用户，耐心和清晰比速度更重要。"""


# ── 智能体构建 ───────────────────────────────────────────

# 缓存（惰性初始化，不在模块加载时创建）
_agent: Optional[Agent] = None


def _build_tools() -> list[Tool]:
    """构建全部文旅工具列表"""
    return [
        create_attraction_guide_tool(),
        create_route_planner_tool(),
        create_cultural_story_tool(),
    ]


def build_tourism_agent(
    llm=None,
    verbose: bool = False,
) -> Agent:
    """
    构建文旅导览智能体

    Args:
        llm: LLM 实例（如未提供则从 ModelFactory 获取）
        verbose: 是否输出详细日志

    Returns:
        Agent 实例，集成景点导览、路线规划、文化故事三个工具
    """
    global _agent
    if _agent is not None and not verbose:
        return _agent

    if llm is None:
        llm = ModelFactory.get_llm()

    tools = _build_tools()

    _agent = Agent(
        llm=llm,
        system_prompt=TOURISM_SYSTEM_PROMPT,
        tools=tools,
        name="文旅导览助手",
        max_iterations=10,
        verbose=verbose,
    )

    logger.info("文旅导览智能体已构建（工具数=%d）" % len(tools))
    return _agent


def _reset_agent():
    """重置智能体缓存（用于测试或配置变更后刷新）"""
    global _agent
    _agent = None


# ── 便捷封装 ────────────────────────────────────────────

class TourismAgent:
    """
    文旅导览智能体便捷封装

    用法：
        agent = TourismAgent()
        result = agent.chat("帮我查一下故宫的门票信息")
        result = agent.chat("规划一个北京两日游")
    """

    def __init__(self, llm=None, verbose: bool = False):
        self._agent = build_tourism_agent(llm=llm, verbose=verbose)
        self._chat_history: list = []

    def chat(self, query: str) -> str:
        """与智能体对话"""
        result = self._agent.run(query, chat_history=self._chat_history)
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
        return self._agent.run(query)
