"""
build_kb — 知识库构建与查询模块
使用 ChromaDB + BGE Embedding 实现向量检索

功能：
1. build_knowledge_base: 从目录加载文档，构建向量库
2. load_knowledge_base: 加载已存在的向量库
3. query_knowledge_base: 检索相关知识片段（返回 Document，含来源元数据）
4. query_knowledge_base_text: 检索并返回纯文本片段
5. _get_chroma_path: 计算某个 collection 的持久化目录
6. _load_documents / _split / _collection_has_data: 内部工具

命名兼容说明
------------
历史代码中同时存在两套参数名，本模块统一支持：
  docs_dir  ==  doc_dir      （源文档目录）
  persist_dir == chroma_dir  （向量库持久化目录）
因此新旧调用点都无需改动。
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, List, Optional

import config

logger = logging.getLogger(__name__)

# ── 默认参数 ────────────────────────────────────────────

_DEFAULT_COLLECTION = "knowledge"
_DEFAULT_PERSIST_DIR = config.KB_CHROMA_DIR
_MAX_QUERY_LEN = 10000  # 查询最大长度
_DEFAULT_TOP_K = 5


def _get_chroma_path(collection_name: str = _DEFAULT_COLLECTION) -> Path:
    """
    返回指定 collection 的向量库持久化目录。

    每个 collection 使用独立子目录，避免多个知识库互相覆盖
    （附件一 §8.2：每个知识库集合独立管理）。

    Args:
        collection_name: collection 名称

    Returns:
        Path，形如 <KB_CHROMA_DIR>/<collection_name>
    """
    safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in str(collection_name))
    if not safe:
        safe = _DEFAULT_COLLECTION
    return Path(config.KB_CHROMA_DIR) / safe


def _resolve_dirs(
    docs_dir: Any = None,
    persist_dir: Any = None,
    doc_dir: Any = None,
    chroma_dir: Any = None,
    collection_name: str = _DEFAULT_COLLECTION,
) -> tuple[Optional[Path], Path]:
    """统一解析文档目录与持久化目录（兼容两套参数名）"""
    src = docs_dir if docs_dir is not None else doc_dir
    dst = persist_dir if persist_dir is not None else chroma_dir
    src_path = Path(src) if src is not None else None
    dst_path = Path(dst) if dst is not None else _get_chroma_path(collection_name)
    return src_path, dst_path


# ── 文档加载 ────────────────────────────────────────────

def _load_documents(docs_dir: str | Path) -> list:
    """从目录加载 .txt/.md 文档，返回 LangChain Document 列表"""
    from langchain_core.documents import Document

    docs_dir = Path(docs_dir)
    if not docs_dir.exists():
        logger.warning(f"知识库目录不存在: {docs_dir}")
        return []

    documents: List[Document] = []
    supported = {".txt", ".md", ".markdown"}

    for file_path in sorted(docs_dir.rglob("*")):
        if file_path.suffix.lower() not in supported:
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
            if not text.strip():
                continue
            rel = file_path.relative_to(docs_dir)
            documents.append(Document(
                page_content=text,
                metadata={"source": str(rel), "category": rel.parts[0] if len(rel.parts) > 1 else ""},
            ))
            logger.debug(f"加载文档: {rel}")
        except Exception as e:
            logger.warning(f"读取文件失败 {file_path}: {e}")

    logger.info(f"从 {docs_dir} 加载了 {len(documents)} 个文档")
    return documents


def _split(documents: list, chunk_size: int = 500, chunk_overlap: int = 80) -> list:
    """将文档切分为较小的片段"""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    logger.info(f"切分为 {len(chunks)} 个片段")
    return chunks


# 向后兼容别名
_split_documents = _split


# ── 向量库检查 ────────────────────────────────────────────

def _collection_has_data(persist_dir: str | Path) -> bool:
    """检查持久化目录是否已有 ChromaDB 数据"""
    persist_dir = Path(persist_dir)
    if not persist_dir.exists():
        return False

    # 检查 chroma.sqlite3 文件是否存在且大小合理
    db_file = persist_dir / "chroma.sqlite3"
    if not db_file.exists():
        return False

    # 文件太小说明没有数据（空库的 sqlite3 通常只有几百字节）
    try:
        size = db_file.stat().st_size
        if size < 2048:
            return False
        return True
    except Exception:
        return False


# ── 知识库构建 ────────────────────────────────────────────

def build_knowledge_base(
    docs_dir: str | Path = None,
    collection_name: str = _DEFAULT_COLLECTION,
    persist_dir: str | Path = None,
    embeddings=None,
    doc_dir: str | Path = None,
    chroma_dir: str | Path = None,
    rebuild: bool = False,
) -> Any:
    """
    构建向量知识库

    Args:
        docs_dir / doc_dir: 源文档目录
        collection_name: ChromaDB collection 名称
        persist_dir / chroma_dir: ChromaDB 持久化目录
        embeddings: Embedding 实例（如未提供则自动创建）
        rebuild: 是否先清空旧数据再重建

    Returns:
        Chroma 向量库实例
    """
    docs_path, persist_path = _resolve_dirs(
        docs_dir=docs_dir, persist_dir=persist_dir,
        doc_dir=doc_dir, chroma_dir=chroma_dir,
        collection_name=collection_name,
    )

    if embeddings is None:
        from base.model_factory import ModelFactory
        embeddings = ModelFactory.get_embeddings()

    persist_path = Path(persist_path)

    # 全量重建：删除旧的持久化目录
    if rebuild and persist_path.exists():
        logger.info(f"重建知识库，清理旧数据: {persist_path}")
        shutil.rmtree(persist_path, ignore_errors=True)

    if docs_path is None:
        logger.warning("未提供文档目录，返回空向量库")
        return _create_empty_store(collection_name, persist_path, embeddings)

    documents = _load_documents(docs_path)
    if not documents:
        logger.warning(f"目录 {docs_path} 无可用文档，返回空向量库")
        return _create_empty_store(collection_name, persist_path, embeddings)

    chunks = _split(documents)

    from langchain_community.vectorstores import Chroma

    persist_path.mkdir(parents=True, exist_ok=True)

    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=str(persist_path),
    )
    logger.info(
        f"知识库构建完成: collection={collection_name}, "
        f"chunks={len(chunks)}, dir={persist_path}"
    )
    return vectordb


def load_knowledge_base(
    collection_name: str = _DEFAULT_COLLECTION,
    persist_dir: str | Path = None,
    embeddings=None,
    docs_dir: str | Path = None,
    doc_dir: str | Path = None,
    chroma_dir: str | Path = None,
) -> Any:
    """
    加载已有的向量知识库

    Args:
        collection_name: ChromaDB collection 名称
        persist_dir / chroma_dir: ChromaDB 持久化目录
        embeddings: Embedding 实例
        docs_dir / doc_dir: 兼容参数（仅用于推断目录，加载时不使用）

    Returns:
        Chroma 向量库实例，若不存在则返回 None
    """
    _, persist_path = _resolve_dirs(
        docs_dir=docs_dir, persist_dir=persist_dir,
        doc_dir=doc_dir, chroma_dir=chroma_dir,
        collection_name=collection_name,
    )
    persist_path = Path(persist_path)

    if not persist_path.exists():
        logger.warning(f"向量库目录不存在: {persist_path}")
        return None

    if not _collection_has_data(persist_path):
        logger.warning(f"向量库目录无有效数据: {persist_path}")
        return None

    if embeddings is None:
        from base.model_factory import ModelFactory
        embeddings = ModelFactory.get_embeddings()

    from langchain_community.vectorstores import Chroma

    vectordb = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(persist_path),
    )
    logger.info(f"知识库已加载: collection={collection_name}, dir={persist_path}")
    return vectordb


def query_knowledge_base(
    query: str,
    top_k: int = _DEFAULT_TOP_K,
    vectordb: Any = None,
    collection_name: str = _DEFAULT_COLLECTION,
    persist_dir: str | Path = None,
    chroma_dir: str | Path = None,
    return_documents: bool = True,
) -> List[Any]:
    """
    检索相关知识片段

    内部会自动加载向量库（如果 vectordb 未提供）。
    支持 similarity_search_with_score 和 similarity_search 两种方法。

    Args:
        query: 查询文本
        top_k: 返回结果数量
        vectordb: 向量库实例（可选，如未提供则自动加载）
        collection_name: ChromaDB collection 名称
        persist_dir / chroma_dir: ChromaDB 持久化目录
        return_documents: True 返回 Document（含 source 元数据），
                          False 返回纯文本字符串列表

    Returns:
        匹配的片段列表（Document 或 str）
    """
    # 输入长度限制
    if not query or not query.strip():
        return []

    query = query.strip()
    if len(query) > _MAX_QUERY_LEN:
        query = query[:_MAX_QUERY_LEN]
        logger.warning(f"查询过长，已截断至 {_MAX_QUERY_LEN} 字符")

    # 惰性加载向量库
    if vectordb is None:
        try:
            vectordb = load_knowledge_base(
                collection_name=collection_name,
                persist_dir=persist_dir,
                chroma_dir=chroma_dir,
            )
        except Exception as e:
            logger.warning(f"加载向量库失败: {e}")
            return []

    if vectordb is None:
        return []

    try:
        # 优先使用 similarity_search_with_score
        if hasattr(vectordb, "similarity_search_with_score"):
            results = vectordb.similarity_search_with_score(query, k=top_k)
            # results 是 [(Document, score), ...] 格式
            pairs = list(results)
            if return_documents:
                return [doc for doc, _score in pairs]
            return [doc.page_content for doc, _score in pairs]
        elif hasattr(vectordb, "similarity_search"):
            results = vectordb.similarity_search(query, k=top_k)
            if return_documents:
                return list(results)
            return [doc.page_content for doc in results]
        else:
            logger.warning("向量库不支持检索方法")
            return []
    except Exception as e:
        logger.warning(f"知识库检索失败: {e}")
        return []


def query_knowledge_base_text(
    query: str,
    top_k: int = _DEFAULT_TOP_K,
    vectordb: Any = None,
    collection_name: str = _DEFAULT_COLLECTION,
    persist_dir: str | Path = None,
    chroma_dir: str | Path = None,
) -> List[str]:
    """检索知识库并返回纯文本片段列表（query_knowledge_base 的文本版）"""
    return query_knowledge_base(
        query=query,
        top_k=top_k,
        vectordb=vectordb,
        collection_name=collection_name,
        persist_dir=persist_dir,
        chroma_dir=chroma_dir,
        return_documents=False,
    )


def _create_empty_store(
    collection_name: str = _DEFAULT_COLLECTION,
    persist_dir: str | Path = _DEFAULT_PERSIST_DIR,
    embeddings=None,
):
    """创建一个空的 Chroma 存储（无文档时使用）"""
    from langchain_community.vectorstores import Chroma

    persist_dir = Path(persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )
