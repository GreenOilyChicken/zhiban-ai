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

        else:
            raise ValueError(f"不支持的 LLM Provider: {provider}")

        logger.info(f"LLM 已初始化: provider={provider}")
        return cls._llm

    @classmethod
    def get_embeddings(cls):
        """获取 BGE Embedding 实例（惰性单例）"""
        if cls._embeddings is not None:
            return cls._embeddings

        from langchain_community.embeddings import HuggingFaceBgeEmbeddings

        cls._embeddings = HuggingFaceBgeEmbeddings(
            model_name=config.BGE_MODEL_NAME,
            model_kwargs={"device": config.EMBEDDING_DEVICE},
            encode_kwargs={"normalize_embeddings": True},
        )

        logger.info(f"Embeddings 已初始化: model={config.BGE_MODEL_NAME}")
        return cls._embeddings

    @classmethod
    def reset(cls):
        """重置缓存（用于测试）"""
        cls._llm = None
        cls._embeddings = None
