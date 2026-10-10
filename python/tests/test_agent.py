"""
test_agent — 测试 Agent 和 PlannerExecutorTeam
"""
import pytest
from unittest.mock import MagicMock, patch

from base.agent_framework import Agent, Tool, PlannerExecutorTeam


class _FakeLLM:
    """测试用 Fake LLM"""
    def invoke(self, messages, **kwargs):
        if isinstance(messages, list) and len(messages) > 1:
            human_msg = messages[-1]
            if isinstance(human_msg, tuple):
                content = f"这是{human_msg[1]}的回答"
            else:
                content = "这是助手的回答"
        else:
            content = "这是助手的回答"
        return MagicMock(content=content)


class _FakeKB:
    """测试用 Fake 向量库"""
    def __init__(self):
        self._docs = [
            {"content": "高血压患者应低盐饮食", "source": "hypertension.txt"},
            {"content": "糖尿病患者应控制血糖", "source": "diabetes.txt"},
            {"content": "冠心病患者应定期复查", "source": "coronary.txt"},
        ]

    def similarity_search_with_score(self, q, k=3):
        results = []
        for d in self._docs[:k]:
            from langchain_core.documents import Document
            doc = Document(page_content=d["content"], metadata={"source": d["source"]})
            results.append((doc, 0.5))
        return results


def test_tool_creates_langchain_tool():
    """测试 Tool 转换为 LangChain Tool"""
    def my_func(query: str = "") -> str:
        return f"result: {query}"

    t = Tool(name="test_tool", description="A test tool", func=my_func)
    lc_tool = t.to_langchain_tool()
    assert lc_tool.name == "test_tool"


def test_agent_no_tools():
    """测试无工具路径的 Agent"""
    llm = _FakeLLM()
    agent = Agent(llm=llm, system_prompt="你是一名助手", name="test")
    result = agent.run("你好")
    assert isinstance(result, str)
    assert len(result) > 0


def test_agent_with_tools():
    """测试有工具路径的 Agent"""
    llm = _FakeLLM()
    tool = Tool(name="search", description="搜索", func=lambda q="": f"搜索结果: {q}")
    agent = Agent(llm=llm, system_prompt="你是一名助手", tools=[tool], max_iterations=5)
    assert len(agent.tools) == 1
    assert agent.max_iterations == 5


def test_agent_infer_name():
    """测试 Agent 名称推断"""
    llm = _FakeLLM()
    agent1 = Agent(llm=llm, system_prompt="政策专家")
    assert agent1.name == "政策专家"

    agent2 = Agent(llm=llm, system_prompt="你是一名政务助手，请回答用户问题")
    assert agent2.name != "你是一名政务助手，请回答用户问题"


def test_planner_executor_team_dispatch():
    """测试 PlannerExecutorTeam 调度"""
    llm = _FakeLLM()

    executor_a = MagicMock(spec=Agent)
    executor_a.name = "政策专家"
    executor_a.run = MagicMock(return_value="这是政策专家的回答")

    executor_b = MagicMock(spec=Agent)
    executor_b.name = "银发顾问"
    executor_b.run = MagicMock(return_value="这是银发顾问的回答")

    team = PlannerExecutorTeam(
        llm=llm,
        executors={"policy": executor_a, "elderly": executor_b},
    )

    result = team.run("高血压患者怎么吃？")
    assert isinstance(result, str)


def test_planner_json_parsing():
    """测试 Planner JSON 解析"""
    llm = _FakeLLM()
    executor = MagicMock(spec=Agent)
    executor.name = "test"
    executor.run = MagicMock(return_value="ok")

    team = PlannerExecutorTeam(llm=llm, executors={"test": executor})

    # 测试标准 JSON
    assert team._parse_json_executor('{"executor": "test", "reason": "ok"}') == "test"

    # 测试 code block
    assert team._parse_json_executor('```json\n{"executor": "test"}\n```') == "test"

    # 测试无效 JSON
    assert team._parse_json_executor("这不是JSON") is None
