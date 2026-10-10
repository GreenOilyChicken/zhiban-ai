"""
rag_server — 向量检索 HTTP 服务

提供 REST API 供 Java 后端调用：
  POST /api/v1/search   向量检索
  GET  /api/v1/health    健康检查
  POST /api/v1/build     构建知识库

使用 FastAPI 框架，支持多线程并发请求。
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import config
from knowledge_base.build_kb import (
    build_knowledge_base,
    load_knowledge_base,
    query_knowledge_base,
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(title="知伴AI RAG检索服务", version="1.0.0")

# ── 线程安全的向量库缓存 ────────────────────────────────

_vectordbs: dict[str, Any] = {}
_vectordb_lock = threading.Lock()

COLLECTION_MAP = {
    "govpolicy": {
        "doc_dir_attr": "KB_POLICY_DIR",
        "default_dir": "knowledge_base/policies",
    },
    "elderly": {
        "doc_dir_attr": "KB_ELDERLY_DIR",
        "default_dir": "knowledge_base/elderly",
    },
    "tourism": {
        "doc_dir_attr": "KB_TOURISM_DIR",
        "default_dir": "knowledge_base/tourism",
    },
}


def _get_vectordb(collection: str = "govpolicy") -> Optional[Any]:
    """线程安全地获取向量库实例（惰性初始化）"""
    if collection in _vectordbs:
        return _vectordbs[collection]

    with _vectordb_lock:
        if collection in _vectordbs:
            return _vectordbs[collection]

        info = COLLECTION_MAP.get(collection)
        if info is None:
            logger.error("未知集合: %s", collection)
            return None

        attr_name = info["doc_dir_attr"]
        doc_dir = getattr(config, attr_name, None) or info["default_dir"]

        logger.info("加载向量库: collection=%s, doc_dir=%s", collection, doc_dir)
        try:
            db = load_knowledge_base(
                doc_dir=doc_dir,
                collection_name=collection,
            )
            if db is not None:
                _vectordbs[collection] = db
                logger.info("向量库加载成功: %s", collection)
            else:
                logger.warning("向量库为空: %s", collection)
            return db
        except Exception as e:
            logger.error("加载向量库失败: %s, 错误: %s", collection, e)
            return None


# ── 请求/响应模型 ────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    topK: int = 5
    collection: str = "govpolicy"
    filter: Optional[dict[str, str]] = None


class SearchResultItem(BaseModel):
    vectorId: Optional[str] = None
    score: float = 0.0
    content: str = ""
    metadata: Optional[dict] = None


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    total: int


class BuildRequest(BaseModel):
    collection: str = "govpolicy"
    rebuild: bool = False


class BuildResponse(BaseModel):
    success: bool
    message: str
    collection: str


# ── API 端点 ─────────────────────────────────────────────

@app.get("/api/v1/health")
def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "service": "zhiban-ai-rag",
        "version": "1.0.0",
        "collections": list(_vectordbs.keys()),
    }


@app.post("/api/v1/search", response_model=SearchResponse)
def search(req: SearchRequest):
    """
    向量检索接口

    请求体:
        query: 检索文本
        topK: 返回结果数量 (默认5)
        collection: 集合名称 (govpolicy/elderly/tourism)
        filter: 元数据过滤 (可选)

    返回:
        results: 检索结果列表
        total: 结果总数
    """
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="query不能为空")

    if len(req.query) > 10000:
        raise HTTPException(status_code=400, detail="query过长，最大10000字符")

    db = _get_vectordb(req.collection)
    if db is None:
        logger.warning("向量库不可用: %s, 返回空结果", req.collection)
        return SearchResponse(results=[], total=0)

    try:
        raw_results = query_knowledge_base(req.query, top_k=req.topK)

        if not raw_results:
            return SearchResponse(results=[], total=0)

        items: list[SearchResultItem] = []
        if isinstance(raw_results, list):
            for r in raw_results:
                if isinstance(r, dict):
                    items.append(SearchResultItem(
                        vectorId=str(r.get("id", r.get("vectorId", ""))),
                        score=float(r.get("score", r.get("similarity", 0.0))),
                        content=str(r.get("content", r.get("page_content", ""))),
                        metadata=r.get("metadata"),
                    ))
                elif hasattr(r, "page_content"):
                    items.append(SearchResultItem(
                        vectorId=str(getattr(r, "id", "")),
                        score=float(getattr(r, "similarity", 0.0)),
                        content=r.page_content,
                        metadata=getattr(r, "metadata", None),
                    ))

        logger.info("检索完成: collection=%s, query=%s..., results=%d",
                     req.collection, req.query[:50], len(items))
        return SearchResponse(results=items, total=len(items))

    except Exception as e:
        logger.error("检索失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"检索失败: {e}")


@app.post("/api/v1/build", response_model=BuildResponse)
def build_kb(req: BuildRequest):
    """
    构建知识库（管理员接口）

    请求体:
        collection: 集合名称
        rebuild: 是否强制重建
    """
    info = COLLECTION_MAP.get(req.collection)
    if info is None:
        raise HTTPException(status_code=400, detail=f"未知集合: {req.collection}")

    attr_name = info["doc_dir_attr"]
    doc_dir = getattr(config, attr_name, None) or info["default_dir"]

    try:
        logger.info("构建知识库: collection=%s, rebuild=%s", req.collection, req.rebuild)
        build_knowledge_base(doc_dir=doc_dir, collection_name=req.collection)

        # 刷新缓存
        with _vectordb_lock:
            if req.collection in _vectordbs:
                del _vectordbs[req.collection]

        _get_vectordb(req.collection)

        return BuildResponse(
            success=True,
            message=f"知识库构建成功: {req.collection}",
            collection=req.collection,
        )
    except Exception as e:
        logger.error("构建知识库失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"构建失败: {e}")


@app.on_event("startup")
def startup_event():
    """启动时预加载默认向量库"""
    logger.info("=" * 50)
    logger.info("知伴AI RAG检索服务启动中...")
    logger.info("  LLM Provider  : %s", config.LLM_PROVIDER)
    logger.info("  BGE Model     : %s", config.BGE_MODEL_NAME)
    logger.info("  Embed Device  : %s", config.EMBEDDING_DEVICE)
    logger.info("  KB Chroma Dir : %s", config.KB_CHROMA_DIR)
    logger.info("=" * 50)

    # 惰性加载：不在启动时强制加载，首次搜索时才加载
    # 如需启动时预加载，取消以下注释：
    # for col in COLLECTION_MAP:
    #     _get_vectordb(col)
    logger.info("向量库采用惰性加载，首次检索时初始化")


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("RAG_HOST", "0.0.0.0")
    port = int(os.getenv("RAG_PORT", "8081"))

    uvicorn.run(
        "rag_server:app",
        host=host,
        port=port,
        log_level="info",
        workers=1,
    )
