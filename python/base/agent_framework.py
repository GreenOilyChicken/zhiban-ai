"""
agent_framework — Agent / Tool / PlannerExecutorTeam 核心抽象

设计要点：
1. Tool 包装普通 Python 函数 → LangChain Tool
2. Agent 支持有工具和无工具两种路径
3. PlannerExecutorTeam 实现 Planner→Executor 调度模式
4. 惰性初始化：不在 import 时创建 LLM 实例
"""
from __future__ import annotations

import json
import re
import logging
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Type, Union, get_args, get_origin, get_type_hints

from langchain_core.tools import tool as langchain_tool_decorator
from pydantic import Field, create_model

logger = logging.getLogger(__name__)


# ── Tool ─────────────────────────────────────────────

class Tool:
    """包装普通函数为 LangChain Tool"""

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable,
        param_descriptions: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        self.name = name
        self.description = description
        self.func = func
        self.param_descriptions = param_descriptions or {}

    def to_langchain_tool(self):
        """转换为 LangChain Tool 对象"""
        type_hints = get_type_hints(self.func)
        params: Dict[str, Tuple[Any, Any]] = {}

        sig_params = list(type_hints.items())
        for param_name, param_type in sig_params:
            if param_name == "return":
                continue
            info = self.param_descriptions.get(param_name, {})
            desc = info.get("description", "")
            required = info.get("required", False)

            if required:
                params[param_name] = (param_type, Field(..., description=desc))
            else:
                params[param_name] = (param_type, Field(default=None, description=desc))

        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", self.name)

        model = create_model(f"{safe_name}_model", **params)

        from langchain_core.tools import StructuredTool

        return StructuredTool.from_function(
            name=self.name,
            description=self.description,
            func=self.func,
            args_schema=model,
        )


# ── Agent ────────────────────────────────────────────

class Agent:
    """
    单一智能体，支持：
    - 有工具路径（AgentExecutor）
    - 无工具路径（直接 LLM invoke）
    """

    def __init__(
        self,
        llm,
        system_prompt: str = "",
        tools: Optional[Sequence[Tool]] = None,
        name: str = "",
        max_iterations: int = 10,
        verbose: bool = False,
    ):
        self.llm = llm
        self.name = name or self._infer_name(system_prompt)
        self.system_prompt = system_prompt
        self.tools = list(tools) if tools else []
        self.max_iterations = max_iterations
        self.verbose = verbose
        self._executor = None

    @staticmethod
    def _infer_name(prompt: str) -> str:
        """如果 prompt 看起来像名字（≤20字且不含'你/You'），则用作 name"""
        if len(prompt) <= 20 and "你" not in prompt and "You" not in prompt and "you" not in prompt:
            return prompt
        return "assistant"

    def _build_executor(self):
        """构建 AgentExecutor（惰性）"""
        if self._executor is not None:
            return self._executor

        from langchain.agents import AgentExecutor, create_tool_calling_agent
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

        lc_tools = [t.to_langchain_tool() for t in self.tools]

        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad", optional=True),
            MessagesPlaceholder("chat_history", optional=True),
        ])

        agent = create_tool_calling_agent(self.llm, lc_tools, prompt)

        def _parsing_error_handler(error) -> str:
            return (
                f"工具调用格式错误：{error}\n"
                "请确保使用正确的工具调用格式。如果不确定，请直接给出文本回复。"
            )

        self._executor = AgentExecutor(
            agent=agent,
            tools=lc_tools,
            max_iterations=self.max_iterations,
            verbose=self.verbose,
            handle_parsing_errors=_parsing_error_handler,
        )
        return self._executor

    def run(self, query: str, chat_history: Optional[List] = None) -> str:
        """执行查询"""
        if not self.tools:
            # 无工具路径：直接 invoke
            try:
                messages = [("system", self.system_prompt)]
                if chat_history:
                    messages.extend(chat_history)
                messages.append(("human", query))
                response = self.llm.invoke(messages)
                return response.content if hasattr(response, "content") else str(response)
            except Exception as e:
                logger.error(f"LLM invoke 失败: {e}")
                return f"抱歉，处理您的问题时出现了错误，请稍后重试。"

        # 有工具路径
        executor = self._build_executor()
        try:
            result = executor.invoke(
                {"input": query, "chat_history": chat_history or []}
            )
            return result.get("output", str(result))
        except Exception as e:
            logger.error(f"AgentExecutor 运行失败: {e}")
            err_msg = str(e)
            if len(err_msg) > 200:
                err_msg = err_msg[:200] + "..."
            return f"处理您的问题时出现了错误：{err_msg}"

    def stream(self, query: str, chat_history: Optional[List] = None):
        """
        流式执行查询，逐块产出文本增量（用于 SSE）。

        有工具时先走完整 Agent 流程（工具调用不适合流式），
        拿到最终结果后按句/块切分产出；无工具时直接走 LLM 流式接口。

        Yields:
            str: 文本增量片段
        """
        # 无工具：直接流式调用 LLM
        if not self.tools:
            try:
                messages = [("system", self.system_prompt)]
                if chat_history:
                    messages.extend(chat_history)
                messages.append(("human", query))
                for chunk in self.llm.stream(messages):
                    text = chunk.content if hasattr(chunk, "content") else str(chunk)
                    if text:
                        yield text
                return
            except Exception as e:
                logger.error(f"LLM 流式调用失败: {e}")
                yield "抱歉，处理您的问题时出现了错误，请稍后重试。"
                return

        # 有工具：先完整执行（含工具调用），再分块产出
        result = self.run(query, chat_history=chat_history)
        for piece in _chunk_text(result):
            yield piece


def _chunk_text(text: str, size: int = 24):
    """
    把完整文本切成便于流式展示的片段。

    优先在标点/换行处断开，避免把句子切得过于零碎。
    """
    if not text:
        return
    buf = ""
    for ch in text:
        buf += ch
        if len(buf) >= size and ch in "。！？；\n，、：":
            yield buf
            buf = ""
        elif len(buf) >= size * 3:
            yield buf
            buf = ""
    if buf:
        yield buf


# ── PlannerExecutorTeam ──────────────────────────────

class PlannerExecutorTeam:
    """
    Planner-Executor 模式：
    1. Planner (LLM) 决定将用户问题路由给哪个 executor
    2. 对应 executor Agent 执行并返回结果
    3. 汇总输出
    """

    def __init__(
        self,
        llm,
        executors: Dict[str, Agent],
        planner_prompt: Optional[str] = None,
        verbose: bool = False,
    ):
        self.llm = llm
        self.executors = executors
        self.verbose = verbose

        self.planner_prompt = planner_prompt or (
            "你是一个调度器。根据用户问题，选择最合适的专家来回答。\n"
            "可选择的专家及其职责：\n{executor_descriptions}\n\n"
            "请返回 JSON 格式：{{\"executor\": \"专家名称\", \"reason\": \"选择原因\"}}\n"
            "只返回 JSON，不要附加其他内容。"
        )

    def _build_executor_descriptions(self) -> str:
        lines = []
        for name, agent in self.executors.items():
            lines.append(f"- {name}: {agent.name}")
        return "\n".join(lines)

    def _plan(self, query: str) -> str:
        """Planner 决定路由到哪个 executor"""
        prompt = self.planner_prompt.format(
            executor_descriptions=self._build_executor_descriptions()
        )

        try:
            response = self.llm.invoke([
                ("system", prompt),
                ("human", query),
            ])
            text = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.warning(f"Planner LLM 调用失败，使用默认 executor: {e}")
            return list(self.executors.keys())[0]

        # 尝试解析 JSON
        executor_name = self._parse_json_executor(text)
        if executor_name:
            if self.verbose:
                logger.info(f"Planner 路由 → {executor_name}")
            return executor_name

        # Fallback: 尝试直接匹配 executor 名
        text_clean = text.strip().strip("\"'")
        for name in self.executors:
            if name in text_clean:
                if self.verbose:
                    logger.info(f"Planner 路由(fallback) → {name}")
                return name

        # 最终 fallback：第一个 executor
        default = list(self.executors.keys())[0]
        logger.warning(f"Planner 无法解析 '{text_clean[:50]}'，使用默认: {default}")
        return default

    def _parse_json_executor(self, text: str) -> Optional[str]:
        """从 LLM 输出中解析 JSON，提取 executor 名"""
        # 尝试提取 ```json ... ``` 块
        json_match = re.search(r"```(?:json|JSON|Json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        json_str = json_match.group(1).strip() if json_match else text.strip()

        # 移除可能的非 JSON 前缀
        brace_idx = json_str.find("{")
        if brace_idx > 0:
            json_str = json_str[brace_idx:]

        try:
            data = json.loads(json_str)
            executor = data.get("executor", "")
            if executor and executor in self.executors:
                return executor
            # 模糊匹配
            for name in self.executors:
                if executor and name in executor:
                    return name
        except (json.JSONDecodeError, AttributeError):
            pass

        return None

    def run(self, query: str, chat_history: Optional[List] = None) -> str:
        """执行：Planner 路由 → Executor 执行"""
        executor_name = self._plan(query)
        agent = self.executors[executor_name]
        result = agent.run(query, chat_history=chat_history)

        prefix = f"[executor={executor_name}]\n"
        return prefix + result
