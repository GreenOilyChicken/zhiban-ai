"""
main — 政务政策智能体 CLI 入口
支持 --build-kb / --rebuild / --verbose 等命令行参数。

用法：
    # 构建知识库
    python -m govpolicy_agent.main --build-kb

    # 重建知识库
    python -m govpolicy_agent.main --build-kb --rebuild

    # 启动交互对话（单 Agent 模式）
    python -m govpolicy_agent.main

    # 启动交互对话（团队模式 + 详细日志）
    python -m govpolicy_agent.main --team --verbose
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import List, Optional

import config
from knowledge_base.build_kb import build_knowledge_base, _get_chroma_path

from .government_agent import (
    build_government_agent,
    _reset_vectordb,
    COLLECTION_NAME,
)
from .government_team import build_government_team

logger = logging.getLogger(__name__)


# ── API Key 预检查 ─────────────────────────────────────

def _check_api_key() -> bool:
    """
    在进入聊天循环前检查 API Key 是否已配置。
    根据当前 LLM_PROVIDER 检查对应的 API Key。

    Returns:
        True 表示已配置，False 表示缺失
    """
    provider = config.LLM_PROVIDER.lower()

    if provider == "deepseek":
        key = config.DEEPSEEK_API_KEY
    elif provider == "openai":
        key = config.OPENAI_API_KEY
    elif provider == "qwen":
        key = config.QWEN_API_KEY
    else:
        print(f"[ERROR] 不支持的 LLM Provider: {provider}")
        return False

    if not key:
        print("=" * 60)
        print("[ERROR] API Key 未配置！")
        print(f"  Provider: {provider}")
        print(f"  请在 .env 文件中设置对应的 API Key：")
        if provider == "deepseek":
            print(f"  DEEPSEEK_API_KEY=sk-xxxx")
        elif provider == "openai":
            print(f"  OPENAI_API_KEY=sk-xxxx")
        elif provider == "qwen":
            print(f"  QWEN_API_KEY=sk-xxxx")
        print("=" * 60)
        return False

    print(f"[OK] API Key 已配置: {config.dump('API Key', key)}")
    return True


# ── 知识库构建 ────────────────────────────────────────

def _build_kb(rebuild: bool = False) -> bool:
    """
    构建政务政策知识库。

    Args:
        rebuild: 是否重建（清除旧数据）
    Returns:
        True 表示成功
    """
    print(f"{'重建' if rebuild else '构建'}政务政策知识库...")

    doc_dir = config.KB_POLICY_DIR
    chroma_dir = _get_chroma_path(COLLECTION_NAME)

    print(f"  文档目录: {doc_dir}")
    print(f"  向量库目录: {chroma_dir}")
    print(f"  Collection: {COLLECTION_NAME}")

    if not doc_dir.exists():
        print(f"[ERROR] 文档目录不存在: {doc_dir}")
        print("  请先在知识库目录下创建政策文档（.txt / .md 文件）。")
        return False

    success = build_knowledge_base(
        doc_dir=doc_dir,
        chroma_dir=chroma_dir,
        rebuild=rebuild,
        collection_name=COLLECTION_NAME,
    )

    if success:
        print("[OK] 知识库构建完成。")
        # 构建后重置向量库缓存，确保下次加载新数据
        _reset_vectordb()
    else:
        print("[ERROR] 知识库构建失败。")

    return success


# ── 交互式聊天循环 ────────────────────────────────────

def _chat_loop(use_team: bool = False, verbose: bool = False) -> None:
    """
    启动交互式聊天循环。

    Args:
        use_team: 是否使用团队模式（Planner-Executor）
        verbose: 是否输出详细日志
    """
    # API Key 预检查
    if not _check_api_key():
        sys.exit(1)

    print()
    print("=" * 60)
    print("  政务政策智能体 — 交互对话")
    print("=" * 60)
    print(f"  模式: {'团队 (Planner-Executor)' if use_team else '单 Agent'}")
    print(f"  Provider: {config.LLM_PROVIDER}")
    print(f"  Model: {_get_model_name()}")
    print("  输入 'quit' 或 'exit' 退出")
    print("  输入 'clear' 清空对话历史")
    print("=" * 60)
    print()

    # 构建智能体（惰性，在确认 API Key 后才创建）
    try:
        if use_team:
            agent_or_team = build_government_team(verbose=verbose)
        else:
            agent_or_team = build_government_agent(verbose=verbose)
    except Exception as e:
        print(f"[ERROR] 智能体初始化失败: {e}")
        sys.exit(1)

    chat_history: List = []

    while True:
        try:
            user_input = input("\n用户> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break

        if user_input.lower() in ("clear", "cls"):
            chat_history.clear()
            print("[OK] 对话历史已清空。")
            continue

        # 执行查询
        try:
            if use_team:
                response = agent_or_team.run(user_input, chat_history=chat_history)
            else:
                response = agent_or_team.run(user_input, chat_history=chat_history)
        except Exception as e:
            logger.error(f"查询执行失败: {e}", exc_info=verbose)
            response = f"处理您的问题时出现错误：{str(e)[:200]}"

        # 输出结果
        print(f"\n助手> {response}")

        # 更新对话历史
        chat_history.append(("human", user_input))
        chat_history.append(("ai", response))

        # 限制对话历史长度（保留最近 20 轮）
        if len(chat_history) > 40:
            chat_history = chat_history[-40:]


def _get_model_name() -> str:
    """获取当前模型名称"""
    provider = config.LLM_PROVIDER.lower()
    if provider == "deepseek":
        return config.DEEPSEEK_MODEL
    elif provider == "openai":
        return config.OPENAI_MODEL
    elif provider == "qwen":
        return config.QWEN_MODEL
    return "unknown"


# ── CLI 入口 ──────────────────────────────────────────

def main(argv: Optional[List[str]] = None) -> int:
    """
    CLI 主入口。

    Args:
        argv: 命令行参数（None 则从 sys.argv 读取）
    Returns:
        退出码
    """
    parser = argparse.ArgumentParser(
        description="政务政策智能体 — 政策检索、法规解读、办事流程咨询、培训台账生成",
    )
    parser.add_argument(
        "--build-kb",
        action="store_true",
        help="构建政务政策知识库",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="重建知识库（清除旧数据，需配合 --build-kb 使用）",
    )
    parser.add_argument(
        "--team",
        action="store_true",
        help="使用团队模式（Planner-Executor 调度）",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="输出详细日志",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="打印配置摘要后退出",
    )

    args = parser.parse_args(argv)

    # 配置日志级别
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # 打印配置摘要
    if args.config:
        config.print_config_summary()
        return 0

    # 构建知识库
    if args.build_kb:
        success = _build_kb(rebuild=args.rebuild)
        return 0 if success else 1

    # 交互对话
    _chat_loop(use_team=args.team, verbose=args.verbose)
    return 0


if __name__ == "__main__":
    sys.exit(main())
