"""
model_factory — LLM & Embedding 工厂
支持 DeepSeek / OpenAI / Qwen 三种 Provider
"""
from __future__ import annotations

import logging
from typing import Optional

import config

logger = logging.getLogger(__name__)


class ModelFactory:
    """创建 LLM 和 Embedding 实例的工厂类"""

    _llm = None
    _embeddings = None

    @classmethod
    def get_llm(cls):
        """获取 LLM 实例（惰性单例）"""
        if cls._llm is not None:
            return cls._llm

        provider = config.LLM_PROVIDER.lower()

        if provider == "deepseek":
            api_key = config.DEEPSEEK_API_KEY
            if not api_key:
                raise ValueError(
                    "DEEPSEEK_API_KEY 未配置！请在 .env 文件中设置。\n"
                    "示例：DEEPSEEK_API_KEY=sk-xxxx"
                )
            from langchain_openai import ChatOpenAI
            cls._llm = ChatOpenAI(
                api_key=api_key,
                base_url=config.DEEPSEEK_BASE_URL,
                model=config.DEEPSEEK_MODEL,
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.LLM_MAX_TOKENS,
            )

        elif provider == "openai":
            api_key = config.OPENAI_API_KEY
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY 未配置！请在 .env 文件中设置。"
                )
            from langchain_openai import ChatOpenAI
            cls._llm = ChatOpenAI(
                api_key=api_key,
                base_url=config.OPENAI_BASE_URL,
                model=config.OPENAI_MODEL,
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.LLM_MAX_TOKENS,
            )

        elif provider == "qwen":
            api_key = config.QWEN_API_KEY
            if not api_key:
                raise ValueError(
                    "QWEN_API_KEY 未配置！请在 .env 文件中设置。"
                )
            from langchain_openai import ChatOpenAI
            cls._llm = ChatOpenAI(
                api_key=api_key,
                base_url=config.QWEN_BASE_URL,
                model=config.QWEN_MODEL,
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.LLM_MAX_TOKENS,
            )

        elif provider == "codebuddy":
            # 本地 CodeBuddy 代理（OpenAI 兼容），用于开发/联调测试
            api_key = config.CODEBUDDY_API_KEY or "codebuddy-local"
            from langchain_openai import ChatOpenAI
            cls._llm = ChatOpenAI(
                api_key=api_key,
                base_url=config.CODEBUDDY_BASE_URL,
                model=config.CODEBUDDY_MODEL,
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.LLM_MAX_TOKENS,
            )

        else:
            raise ValueError(f"不支持的 LLM Provider: {provider}")

        logger.info(f"LLM 已初始化: provider={provider}")
        return cls._llm

    @classmethod
    def get_embeddings(cls):
        """
        获取 Embedding 实例（惰性单例）

        按 config.EMBEDDING_PROVIDER 选择：
          - bge  : HuggingFaceBgeEmbeddings（生产默认，中文语义检索）
          - hash : 确定性哈希向量（离线兜底，仅用于链路验证）
        """
        if cls._embeddings is not None:
            return cls._embeddings

        provider = getattr(config, "EMBEDDING_PROVIDER", "bge")

        if provider == "hash":
            return cls._build_hash_embeddings()

        try:
            from langchain_community.embeddings import HuggingFaceBgeEmbeddings
        except Exception as exc:
            logger.error(
                "BGE 依赖缺失（%s: %s），已降级为 hash 兜底向量，检索质量将显著下降。"
                "生产环境请确认镜像内已安装 sentence-transformers 与 torch。",
                type(exc).__name__, exc,
            )
            return cls._build_hash_embeddings()

        try:
            cls._embeddings = HuggingFaceBgeEmbeddings(
                model_name=config.BGE_MODEL_NAME,
                model_kwargs={"device": config.EMBEDDING_DEVICE},
                encode_kwargs={"normalize_embeddings": True},
            )
        except Exception as exc:
            logger.error(
                "BGE 模型加载失败（%s: %s），已降级为 hash 兜底向量，检索质量将显著下降。"
                "请检查模型目录 %s 是否随镜像分发（客户环境无外网，不能依赖在线下载）。",
                type(exc).__name__, exc, getattr(config, "BGE_MODEL_DIR", "?"),
            )
            return cls._build_hash_embeddings()

        logger.info(f"Embeddings 已初始化: model={config.BGE_MODEL_NAME}")
        return cls._embeddings

    @classmethod
    def _build_hash_embeddings(cls):
        """构造 hash 兜底向量（无外部依赖，仅保证链路可用）"""
        from base.hash_embeddings import HashEmbeddings

        cls._embeddings = HashEmbeddings(dim=getattr(config, "HASH_EMBEDDING_DIM", 512))
        logger.warning(
            "Embeddings 使用离线兜底实现（hash, dim=%d）：仅用于链路验证，"
            "生产环境请设置 EMBEDDING_PROVIDER=bge 并提供模型文件",
            getattr(config, "HASH_EMBEDDING_DIM", 512),
        )
        return cls._embeddings

    @classmethod
    def reset(cls):
        """重置缓存（用于测试）"""
        cls._llm = None
        cls._embeddings = None
