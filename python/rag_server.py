"""
rag_server — 向量检索 + 智能体 HTTP 服务

提供 REST API 供 Java 后端调用：
  GET  /api/v1/health     健康检查
  POST /api/v1/search     向量检索
  POST /api/v1/build      构建知识库
  POST /api/v1/chat       智能体对话（康养/政务/文旅）
  GET  /api/v1/agents     智能体列表
  POST /api/v1/tts        文本转语音
  POST /api/v1/asr        语音识别
  GET  /api/v1/speakers   发音人列表

使用 FastAPI 框架，支持多线程并发请求。
"""
from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import Response, StreamingResponse
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

app = FastAPI(title="知伴AI 智能体与RAG服务", version="1.1.0")

# ── 线程安全的向量库缓存 ────────────────────────────────

_vectordbs: dict[str, Any] = {}
_vectordb_lock = threading.Lock()

# collection -> 源文档目录（与 config.KB_COLLECTIONS 对齐）
COLLECTION_MAP = {
    config.COLLECTION_GOVPOLICY: {"doc_dir_attr": "KB_POLICY_DIR"},
    config.COLLECTION_ELDERLY: {"doc_dir_attr": "KB_ELDERLY_DIR"},
    config.COLLECTION_TOURISM: {"doc_dir_attr": "KB_TOURISM_DIR"},
}

# 兼容旧集合名（历史数据/旧客户端）
COLLECTION_ALIASES = {
    "govpolicy": config.COLLECTION_GOVPOLICY,
    "elderly_care": config.COLLECTION_ELDERLY,
    "elderly": config.COLLECTION_ELDERLY,
    "tourism": config.COLLECTION_TOURISM,
}


def _normalize_collection(name: str) -> str:
    """把传入的集合名归一化为规范名"""
    return COLLECTION_ALIASES.get(name, name)


def _doc_dir_for(collection: str) -> Path:
    """返回某集合对应的源文档目录"""
    info = COLLECTION_MAP.get(collection, {})
    attr = info.get("doc_dir_attr")
    if attr:
        val = getattr(config, attr, None)
        if val:
            return Path(val)
    return Path(config.KB_CHROMA_DIR).parent / collection


def _get_vectordb(collection: str = None) -> Optional[Any]:
    """线程安全地获取向量库实例（惰性初始化）"""
    collection = _normalize_collection(collection or config.COLLECTION_GOVPOLICY)

    if collection in _vectordbs:
        return _vectordbs[collection]

    with _vectordb_lock:
        if collection in _vectordbs:
            return _vectordbs[collection]

        if collection not in COLLECTION_MAP:
            logger.error("未知集合: %s", collection)
            return None

        doc_dir = _doc_dir_for(collection)
        persist_dir = config.KB_CHROMA_DIR / collection

        logger.info("加载向量库: collection=%s, dir=%s", collection, persist_dir)
        try:
            db = load_knowledge_base(
                collection_name=collection,
                persist_dir=persist_dir,
            )
            if db is not None:
                _vectordbs[collection] = db
                logger.info("向量库加载成功: %s", collection)
            else:
                logger.warning("向量库为空: %s (doc_dir=%s)", collection, doc_dir)
            return db
        except Exception as e:
            logger.error("加载向量库失败: %s, 错误: %s", collection, e)
            return None


def _drop_cache(collection: str) -> None:
    """清除某集合的向量库缓存"""
    with _vectordb_lock:
        _vectordbs.pop(collection, None)


# ── 请求/响应模型 ────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    topK: int = 5
    collection: str = config.COLLECTION_GOVPOLICY
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
    collection: str = config.COLLECTION_GOVPOLICY
    rebuild: bool = False


class BuildResponse(BaseModel):
    success: bool
    message: str
    collection: str


# ── 智能体对话模型 ────────────────────────────────────────

class ChatRequest(BaseModel):
    """智能体对话请求（Java 后端 /api/chat/send 转发）"""
    message: str
    agent: str = "elderly"          # elderly / govpolicy / tourism
    history: Optional[list] = None  # [{"role": "user"/"assistant", "content": "..."}]
    sessionId: Optional[str] = None


class ChatResponse(BaseModel):
    content: str
    agent: str
    model: str = ""
    references: list[str] = []


# ── API 端点 ─────────────────────────────────────────────

@app.get("/api/v1/health")
def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "service": "zhiban-ai-agent",
        "version": "1.1.0",
        "llmProvider": config.LLM_PROVIDER,
        "collections": list(COLLECTION_MAP.keys()),
        "loaded": list(_vectordbs.keys()),
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

    collection = _normalize_collection(req.collection)
    db = _get_vectordb(collection)
    if db is None:
        logger.warning("向量库不可用: %s, 返回空结果", collection)
        return SearchResponse(results=[], total=0)

    try:
        docs = query_knowledge_base(
            query=req.query,
            top_k=req.topK,
            vectordb=db,
            collection_name=collection,
        )

        if not docs:
            return SearchResponse(results=[], total=0)

        items: list[SearchResultItem] = []
        for i, doc in enumerate(docs):
            metadata = dict(getattr(doc, "metadata", None) or {})
            source = metadata.get("source", "")
            if source and ("/" in source or "\\" in source):
                metadata["source"] = Path(source).name

            # 元数据过滤（如 policy_type / category）
            if req.filter:
                if any(str(metadata.get(k, "")) != str(v) for k, v in req.filter.items()):
                    continue

            items.append(SearchResultItem(
                vectorId=str(metadata.get("vector_id", metadata.get("source", f"{collection}-{i}"))),
                score=float(metadata.get("score", 0.0)),
                content=doc.page_content,
                metadata=metadata,
            ))

        logger.info("检索完成: collection=%s, query=%s..., results=%d",
                    collection, req.query[:50], len(items))
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
    collection = _normalize_collection(req.collection)
    if collection not in COLLECTION_MAP:
        raise HTTPException(status_code=400, detail=f"未知集合: {req.collection}")

    doc_dir = _doc_dir_for(collection)
    persist_dir = config.KB_CHROMA_DIR / collection

    try:
        logger.info("构建知识库: collection=%s, rebuild=%s, dir=%s",
                    collection, req.rebuild, persist_dir)
        build_knowledge_base(
            docs_dir=doc_dir,
            collection_name=collection,
            persist_dir=persist_dir,
            rebuild=req.rebuild,
        )

        # 刷新缓存
        _drop_cache(collection)
        _get_vectordb(collection)

        return BuildResponse(
            success=True,
            message=f"知识库构建成功: {collection}",
            collection=collection,
        )
    except Exception as e:
        logger.error("构建知识库失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"构建失败: {e}")


# ── 智能体对话 ───────────────────────────────────────────

# 惰性构建的智能体缓存
_agents: dict[str, Any] = {}
_agents_lock = threading.Lock()

AGENT_ALIASES = {
    "elderly": "elderly",
    "elderly_care": "elderly",
    "health": "elderly",
    "康养": "elderly",
    "银发": "elderly",
    "govpolicy": "govpolicy",
    "gov": "govpolicy",
    "government": "govpolicy",
    "policy": "govpolicy",
    "政务": "govpolicy",
    "tourism": "tourism",
    "travel": "tourism",
    "文旅": "tourism",
}


def _normalize_agent(name: str) -> str:
    return AGENT_ALIASES.get((name or "").strip().lower(), "elderly")


def _get_agent(agent: str):
    """线程安全地构建/获取智能体实例"""
    agent = _normalize_agent(agent)
    if agent in _agents:
        return _agents[agent]

    with _agents_lock:
        if agent in _agents:
            return _agents[agent]

        logger.info("初始化智能体: %s", agent)
        if agent == "elderly":
            from elderly_agent.elderly_agent import build_elderly_agent
            instance = build_elderly_agent()
        elif agent == "govpolicy":
            from govpolicy_agent.government_agent import build_government_agent
            instance = build_government_agent()
        elif agent == "tourism":
            from tourism_agent.tourism_agent import build_tourism_agent
            instance = build_tourism_agent()
        else:
            raise HTTPException(status_code=400, detail=f"未知智能体: {agent}")

        _agents[agent] = instance
        return instance


def _to_chat_history(history: Optional[list]):
    """把 JSON 历史转为 LangChain 消息列表"""
    if not history:
        return []
    try:
        from langchain_core.messages import AIMessage, HumanMessage
    except Exception:
        return []

    messages = []
    for item in history[-20:]:  # 至少保留 10 轮（20 条）
        if not isinstance(item, dict):
            continue
        role = item.get("role", "user")
        content = item.get("content", "")
        if not content:
            continue
        if role in ("assistant", "ai", "bot"):
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
    return messages


@app.get("/api/v1/agents")
def list_agents():
    """智能体列表（供前端展示）"""
    return {
        "agents": [
            {"key": "elderly", "name": "银发康养智能体", "desc": "用药指导、护理建议、康复计划、长护险"},
            {"key": "govpolicy", "name": "政务政策智能体", "desc": "政策检索、培训台账"},
            {"key": "tourism", "name": "文旅导览智能体", "desc": "景点导览、路线规划、文化故事"},
        ]
    }


@app.post("/api/v1/chat", response_model=ChatResponse)
def agent_chat(req: ChatRequest):
    """
    智能体对话接口

    请求体:
        message: 用户消息
        agent: 智能体标识 (elderly/govpolicy/tourism)
        history: 对话历史（可选，保留上下文）
        sessionId: 会话ID（可选）

    返回:
        content: 智能体回复
        agent: 实际使用的智能体
        references: 引用的知识来源
    """
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message不能为空")

    agent_key = _normalize_agent(req.agent)
    try:
        agent = _get_agent(agent_key)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("智能体初始化失败: %s", e, exc_info=True)
        raise HTTPException(status_code=503, detail=f"智能体不可用: {e}")

    try:
        history = _to_chat_history(req.history)
        reply = agent.run(req.message.strip(), chat_history=history)
        return ChatResponse(
            content=reply or "",
            agent=agent_key,
            model=config.LLM_PROVIDER,
            references=[],
        )
    except Exception as e:
        logger.error("智能体对话失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"对话失败: {e}")


@app.post("/api/v1/chat/stream")
def agent_chat_stream(req: ChatRequest):
    """
    智能体对话（SSE 流式）

    以 text/event-stream 逐块返回，事件格式：
        data: {"delta": "文本片段", "done": false}
        data: {"delta": "", "done": true, "agent": "tourism"}
    """
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message不能为空")

    agent_key = _normalize_agent(req.agent)
    history = _to_chat_history(req.history)
    message = req.message.strip()

    def event_stream():
        import json as _json
        try:
            agent = _get_agent(agent_key)
        except Exception as e:
            logger.error("智能体初始化失败: %s", e, exc_info=True)
            yield f"data: {_json.dumps({'delta': '', 'done': True, 'error': str(e)}, ensure_ascii=False)}\n\n"
            return

        try:
            for piece in agent.stream(message, chat_history=history):
                if piece:
                    payload = {"delta": piece, "done": False, "agent": agent_key}
                    yield f"data: {_json.dumps(payload, ensure_ascii=False)}\n\n"
            yield f"data: {_json.dumps({'delta': '', 'done': True, 'agent': agent_key}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error("智能体流式对话失败: %s", e, exc_info=True)
            payload = {"delta": "", "done": True, "error": str(e)[:200]}
            yield f"data: {_json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── 语音（TTS / ASR） ────────────────────────────────────

@app.get("/api/v1/speakers")
def list_speakers():
    """可用发音人列表"""
    from voice_service import list_voices
    return {"speakers": list_voices()}


@app.post("/api/v1/tts")
def text_to_speech(payload: dict):
    """
    文本转语音

    请求体: {"text": "...", "speaker": "zh-CN-XiaoxiaoNeural"}
    返回: audio/mpeg 二进制
    """
    text = (payload or {}).get("text", "")
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="text不能为空")

    speaker = (payload or {}).get("speaker") or None
    try:
        from voice_service import synthesize
        audio = synthesize(text.strip(), voice=speaker)
    except Exception as e:
        logger.error("TTS 合成失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"TTS失败: {e}")

    if not audio:
        raise HTTPException(status_code=500, detail="TTS 未返回音频")

    return Response(content=audio, media_type="audio/mpeg",
                    headers={"Content-Disposition": 'inline; filename="tts.mp3"'})


@app.post("/api/v1/asr")
async def speech_to_text(file: UploadFile = File(...)):
    """
    语音识别

    表单: file=<音频文件> (wav/mp3/m4a 等)
    返回: {"text": "识别结果"}
    """
    try:
        data = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取上传文件失败: {e}")

    if not data:
        raise HTTPException(status_code=400, detail="音频文件为空")

    try:
        from voice_service import transcribe
        text = transcribe(data, filename=file.filename or "audio.wav")
    except Exception as e:
        logger.error("ASR 识别失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"ASR失败: {e}")

    return {"text": text or ""}


@app.on_event("startup")
def startup_event():
    """启动时打印配置摘要"""
    logger.info("=" * 50)
    logger.info("知伴AI 智能体与RAG服务启动中...")
    logger.info("  LLM Provider  : %s", config.LLM_PROVIDER)
    logger.info("  LLM Base URL  : %s", _llm_base_url())
    logger.info("  BGE Model     : %s", config.BGE_MODEL_NAME)
    logger.info("  Embed Device  : %s", config.EMBEDDING_DEVICE)
    logger.info("  KB Chroma Dir : %s", config.KB_CHROMA_DIR)
    logger.info("  Collections   : %s", ", ".join(COLLECTION_MAP.keys()))
    logger.info("=" * 50)
    logger.info("向量库采用惰性加载，首次检索时初始化")


def _llm_base_url() -> str:
    if config.LLM_PROVIDER == "openai":
        return config.OPENAI_BASE_URL
    if config.LLM_PROVIDER == "qwen":
        return config.QWEN_BASE_URL
    return config.DEEPSEEK_BASE_URL


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
