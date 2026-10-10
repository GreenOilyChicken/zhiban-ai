"""
government_agent — 政务政策智能体主模块
提供政策检索（RAG）与季度培训台账生成两大工具。

设计要点：
1. 线程安全的向量库访问（threading.Lock 保护 _vectordb 全局变量）
2. 搜索查询输入长度限制（max 10000 字符）
3. create_quarterly_ledgers 异常处理
4. 不在模块级实例化 Agent
5. 搜索结果使用文件名而非完整路径（不泄露目录信息）
6. RAG 查询返回带来源归属的格式化结果
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import config
from base.agent_framework import Agent, Tool
from base.model_factory import ModelFactory
from knowledge_base.build_kb import (
    build_knowledge_base,
    load_knowledge_base,
    query_knowledge_base,
    _get_chroma_path,
)

from .training_ledger.ledger_generator import LedgerGenerator

logger = logging.getLogger(__name__)

# ── 常量 ──────────────────────────────────────────────

MAX_QUERY_LENGTH = 10000
COLLECTION_NAME = "govpolicy"

# ── 线程安全的向量库缓存 ──────────────────────────────

_vectordb = None
_vectordb_lock = threading.Lock()


def _get_vectordb():
    """
    获取向量库实例（线程安全）。
    使用 threading.Lock 保护全局 _vectordb，确保多线程下只初始化一次。
    """
    global _vectordb
    if _vectordb is not None:
        return _vectordb

    with _vectordb_lock:
        # double-check 模式
        if _vectordb is not None:
            return _vectordb
        logger.info("初始化政务政策向量库...")
        _vectordb = load_knowledge_base(
            doc_dir=config.KB_POLICY_DIR,
            chroma_dir=_get_chroma_path(COLLECTION_NAME),
            collection_name=COLLECTION_NAME,
        )
        if _vectordb is None:
            logger.error("向量库初始化失败")
        return _vectordb


def _reset_vectordb():
    """重置向量库缓存（用于测试或重建后刷新）"""
    global _vectordb
    with _vectordb_lock:
        _vectordb = None


# ── 工具：政策检索 ────────────────────────────────────

def _search_policy_db(query: str, top_k: int = 5) -> str:
    """
    检索政务政策知识库，返回匹配的政策文档片段。

    Args:
        query: 检索关键词或问题
        top_k: 返回结果数量，默认5
    Returns:
        格式化的检索结果，包含来源归属
    """
    if not query or not query.strip():
        return "检索内容为空，请提供检索关键词。"

    # 输入长度限制
    if len(query) > MAX_QUERY_LENGTH:
        logger.warning(
            f"检索查询过长（{len(query)}字符），截断至 {MAX_QUERY_LENGTH} 字符"
        )
        query = query[:MAX_QUERY_LENGTH]

    try:
        vs = _get_vectordb()
        if vs is None:
            return "知识库未就绪，请先使用 --build-kb 构建知识库。"

        docs = query_knowledge_base(
            query=query,
            chroma_dir=_get_chroma_path(COLLECTION_NAME),
            collection_name=COLLECTION_NAME,
            top_k=top_k,
        )

        if not docs:
            return f"未找到与「{query[:50]}」相关的政策文档。"

        # 格式化结果，使用文件名而非完整路径
        formatted_parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "未知来源")
            # 确保只显示文件名，不泄露目录路径
            if source and ("/" in source or "\\" in source):
                source = Path(source).name

            category = doc.metadata.get("category", "")
            content = doc.page_content.strip()

            header = f"【结果 {i}】来源：{source}"
            if category:
                header += f" | 分类：{category}"
            formatted_parts.append(f"{header}\n{content}")

        result_text = "\n\n---\n\n".join(formatted_parts)
        result_text += f"\n\n---\n共找到 {len(docs)} 条相关结果。"
        return result_text

    except Exception as e:
        logger.error(f"政策检索失败: {e}")
        return f"政策检索时出现错误：{str(e)[:200]}"


search_policy_db_tool = Tool(
    name="search_policy_db",
    description=(
        "检索政务政策知识库。当用户询问政策内容、法规条文、办事流程等"
        "需要查找政策文档的问题时使用此工具。"
        "输入：检索关键词或问题描述。"
    ),
    func=_search_policy_db,
    param_descriptions={
        "query": {
            "description": "检索关键词或问题描述",
            "required": True,
        },
        "top_k": {
            "description": "返回结果数量，默认5",
            "required": False,
        },
    },
)


# ── 工具：生成季度培训台账 ────────────────────────────

def _create_quarterly_ledgers(
    quarter: str,
    unit_name: str = "",
    topics: Optional[List[Tuple[str, List[str], str]]] = None,
) -> str:
    """
    生成季度培训台账 Word 文档。

    Args:
        quarter: 季度字符串，如 "2026Q1" 或 "2026-Q1"
        unit_name: 培训单位名称
        topics: 培训主题列表，每项为 (主题名, 参训人员列表, 培训日期)
    Returns:
        生成结果提示信息（含文件路径）
    """
    try:
        if not quarter or not quarter.strip():
            return "错误：季度参数不能为空，请提供如 '2026Q1' 的季度信息。"

        gen = LedgerGenerator()
        output_path = gen.generate(
            quarter=quarter.strip(),
            unit_name=unit_name or "未指定单位",
            topics=topics,
        )

        return (
            f"培训台账已生成：{output_path}\n"
            f"季度：{quarter}\n"
            f"单位：{unit_name or '未指定'}\n"
            f"培训主题数：{len(topics) if topics else 0}"
        )

    except ValueError as e:
        logger.error(f"台账生成参数错误: {e}")
        return f"参数错误：{str(e)[:200]}"
    except RuntimeError as e:
        logger.error(f"台账生成运行错误: {e}")
        return f"生成失败：{str(e)[:200]}"
    except Exception as e:
        logger.error(f"台账生成未知错误: {e}", exc_info=True)
        return f"生成培训台账时出现未知错误：{str(e)[:200]}"


create_quarterly_ledgers_tool = Tool(
    name="create_quarterly_ledgers",
    description=(
        "生成季度培训台账 Word 文档。当用户需要创建培训记录、"
        "季度台账或培训签到表时使用此工具。"
        "输入：季度（如 2026Q1）、单位名称、培训主题列表。"
    ),
    func=_create_quarterly_ledgers,
    param_descriptions={
        "quarter": {
            "description": "季度字符串，如 '2026Q1' 或 '2026-Q1'",
            "required": True,
        },
        "unit_name": {
            "description": "培训单位名称",
            "required": False,
        },
        "topics": {
            "description": "培训主题列表，每项为 (主题名, 参训人员列表, 培训日期)",
            "required": False,
        },
    },
)


# ── Agent 构建 ────────────────────────────────────────

GOVERNMENT_AGENT_SYSTEM_PROMPT = """\
你是一个专业的政务政策智能助手。你的职责包括：

1. **政策检索**：使用 search_policy_db 工具检索政策知识库，回答用户关于政策、法规的问题。
2. **培训台账生成**：使用 create_quarterly_ledgers 工具生成季度培训台账 Word 文档。

**工作原则：**
- 涉及政策、法规、办事流程的问题，优先使用 search_policy_db 工具检索知识库，基于检索结果回答。
- 回答时标注信息来源（文件名），确保可追溯。
- 如果知识库中未找到相关信息，如实告知用户，不要编造。
- 生成培训台账时，确认季度信息、单位名称和培训主题。
- 保持专业、准确、客观的语气。

**输出格式：**
- 政策咨询：先给出检索到的相关信息，再进行归纳总结，标注来源。
- 台账生成：确认生成成功并告知文件路径。
"""

GOVERNMENT_AGENT_TOOLS: Sequence[Tool] = [
    search_policy_db_tool,
    create_quarterly_ledgers_tool,
]


def build_government_agent(verbose: bool = False) -> Agent:
    """
    构建政务政策智能体（惰性，不在模块级实例化）。

    Args:
        verbose: 是否输出详细日志
    Returns:
        配置好的 Agent 实例
    """
    llm = ModelFactory.get_llm()
    return Agent(
        llm=llm,
        system_prompt=GOVERNMENT_AGENT_SYSTEM_PROMPT,
        tools=list(GOVERNMENT_AGENT_TOOLS),
        name="政务政策助手",
        max_iterations=10,
        verbose=verbose,
    )
