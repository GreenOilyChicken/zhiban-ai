FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 优先使用锁定版本，保证可复现构建
COPY requirements.txt requirements.lock.txt ./
RUN pip install --no-cache-dir --user -r requirements.lock.txt

# ── 运行阶段 ──────────────────────────────

FROM python:3.11-slim

LABEL maintainer="zhiban-ai"
LABEL description="知伴AI 智能体与RAG服务"

WORKDIR /app

# ffmpeg：ASR 音频格式转换依赖
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 复制 pip 安装的包
COPY --from=builder /root/.local /root/.local

# 复制项目文件
COPY . .

# 环境变量
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV RAG_HOST=0.0.0.0
ENV RAG_PORT=8081
# 生产默认使用 BGE 语义向量；离线环境可覆盖为 hash
ENV EMBEDDING_PROVIDER=bge

# 知识库默认路径（容器内）
ENV KB_POLICY_DIR=/app/knowledge_base/policies
ENV KB_ELDERLY_DIR=/app/knowledge_base/elderly
ENV KB_TOURISM_DIR=/app/knowledge_base/tourism
ENV KB_CHROMA_DIR=/app/knowledge_base/chroma_db
ENV LEDGER_OUTPUT_DIR=/app/output/ledgers

# 创建必要目录
RUN mkdir -p /app/knowledge_base/chroma_db /app/output/ledgers

EXPOSE 8081

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8081/api/v1/health')" || exit 1

CMD ["python", "rag_server.py"]
