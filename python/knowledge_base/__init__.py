"""
knowledge_base — 知识库构建与查询模块
使用 ChromaDB + BGE Embedding 实现向量检索
"""
from .build_kb import build_knowledge_base, load_knowledge_base, query_knowledge_base

__all__ = ["build_knowledge_base", "load_knowledge_base", "query_knowledge_base"]
