"""
main — 银发康养智能体 CLI 入口

用法：
  python -m elderly_agent.main [选项] [问题]

选项：
  --build-kb       构建知识库（需要先准备文档文件）
  --rebuild         重建知识库（删除旧数据后重建）
  --verbose         详细日志输出
  --team            使用 Planner-Executor 团队模式（默认使用单一 Agent）
  --max-iterations   Agent 最大迭代次数（默认 10）
  --help, -h        显示帮助

示例：
  python -m elderly_agent.main 我妈 72 岁，高血压+糖尿病，在吃阿司匹林和二甲双胍，安全吗？
  python -m elderly_agent.main --team 髋关节置换术后 3 周怎么康复？
  python -m elderly_agent.main --build-kb
  python -m elderly_agent.main --verbose 华法林和阿司匹林能一起吃吗？
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import List, Optional

import config
from base.model_factory import ModelFactory

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool = False):
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # 降低第三方库日志级别
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def _build_kb(rebuild: bool = False) -> bool:
    """构建银发康养知识库"""
    from pathlib import Path

    doc_dir = config.KB_ELDERLY_DIR
    if not doc_dir.exists():
        print(f"[!] 文档目录不存在: {doc_dir}")
        print("    请先创建文档目录并放入 .txt / .md 格式的护理知识文档。")
        print("    示例路径: knowledge_base/elderly/policies/")

        # 创建目录结构提示
        print("\n    建议的目录结构：")
        print("    knowledge_base/elderly/")
        print("      ├── policies/        (护理政策文档)")
        print("      ├── hypertension/    (高血压相关)")
        print("      ├── diabetes/        (糖尿病相关)")
        print("      └── ...")

        # 尝试创建空目录
        doc_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n    已创建空目录: {doc_dir}")
        print("    请将文档放入后重新运行 --build-kb。")
        return False

    # 检查文档数量
    doc_count = 0
    for ext in ("*.txt", "*.md", "*.markdown"):
        doc_count += sum(1 for _ in doc_dir.rglob(ext))

    if doc_count == 0:
        print(f"[!] 文档目录为空: {doc_dir}")
        print("    请先准备护理知识文档（.txt 或 .md 格式）后重试。")
        return False

    print(f"[1] 开始构建知识库...")
    print(f"    文档目录: {doc_dir}")
    print(f"    文档数量: {doc_count}")
    print(f"    Chroma 存储: {config.KB_ELDERLY_DIR / 'chroma_db'}")

    try:
        from knowledge_base.build_kb import build_knowledge_base

        success = build_knowledge_base(
            doc_dir=doc_dir,
            chroma_dir=config.KB_ELDERLY_DIR / "chroma_db",
            rebuild=rebuild,
            collection_name="elderly_care",
        )
        if success:
            print("[OK] 知识库构建完成！")
        else:
            print("[FAIL] 知识库构建失败，请查看日志。")
        return success
    except Exception as e:
        print(f"[ERROR] 知识库构建出错: {e}")
        logger.error(f"知识库构建失败: {e}", exc_info=True)
        return False


def _run_query(
    query: str,
    use_team: bool = False,
    max_iterations: int = 10,
    verbose: bool = False,
) -> str:
    """执行用户查询"""
    try:
        if use_team:
            from .elderly_team import build_elderly_team
            team = build_elderly_team(max_iterations=max_iterations, verbose=verbose)
            result = team.run(query)
        else:
            from .elderly_agent import build_elderly_agent
            agent = build_elderly_agent(max_iterations=max_iterations, verbose=verbose)
            result = agent.run(query)
        return result
    except ValueError as e:
        if "API_KEY" in str(e) or "未配置" in str(e):
            return (
                f"[配置错误] {e}\n\n"
                "请在项目根目录创建 .env 文件并配置 LLM Provider。\n"
                "示例（DeepSeek）：\n"
                "  LLM_PROVIDER=deepseek\n"
                "  DEEPSEEK_API_KEY=sk-xxxx\n"
            )
        raise


def _run_interactive(
    use_team: bool = False,
    max_iterations: int = 10,
    verbose: bool = False,
):
    """交互式对话模式"""
    print("=" * 60)
    print("  知伴AI · 银发康养智能体")
    print("  输入您的问题，输入 'quit' 或 'exit' 退出")
    print("=" * 60)
    print()

    # 保留对话历史
    chat_history: List = []

    while True:
        try:
            user_input = input("您> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break

        print()
        try:
            if use_team:
                from .elderly_team import build_elderly_team
                team = build_elderly_team(max_iterations=max_iterations, verbose=verbose)
                response = team.run(user_input, chat_history=chat_history)
            else:
                from .elderly_agent import build_elderly_agent
                agent = build_elderly_agent(max_iterations=max_iterations, verbose=verbose)
                response = agent.run(user_input, chat_history=chat_history)

            print(f"助手> {response}")
            print()

            # 更新对话历史（保留最近 10 轮）
            chat_history.append(("human", user_input))
            chat_history.append(("ai", response))
            if len(chat_history) > 20:
                chat_history = chat_history[-20:]

        except Exception as e:
            print(f"[错误] {e}")
            logger.error(f"查询失败: {e}", exc_info=True)
            print()


def main(argv: Optional[List[str]] = None):
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        prog="elderly_agent",
        description="知伴AI · 银发康养智能体 — 老年人用药安全、护理建议、康复计划、长护险",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python -m elderly_agent.main 我妈在吃华法林，能同时吃阿司匹林吗？\n"
            "  python -m elderly_agent.main --team 髋关节置换术后康复\n"
            "  python -m elderly_agent.main --build-kb\n"
            "  python -m elderly_agent.main --verbose --rebuild\n"
        ),
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="用户问题（如不提供则进入交互模式）",
    )
    parser.add_argument(
        "--build-kb",
        action="store_true",
        help="构建银发康养知识库",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="重建知识库（删除旧数据后重新构建）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="详细日志输出",
    )
    parser.add_argument(
        "--team",
        action="store_true",
        help="使用 Planner-Executor 团队模式（默认使用单一 Agent）",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=10,
        help="Agent 最大迭代次数（默认 10）",
    )

    args = parser.parse_args(argv)
    _setup_logging(verbose=args.verbose)

    # 显示配置摘要
    config.print_config_summary()
    print()

    # ── 构建知识库模式 ──
    if args.build_kb or args.rebuild:
        success = _build_kb(rebuild=args.rebuild)
        if not success:
            sys.exit(1)
        if not args.query:
            return

    # ── 单次查询模式 ──
    query = " ".join(args.query).strip()
    if query:
        result = _run_query(
            query,
            use_team=args.team,
            max_iterations=args.max_iterations,
            verbose=args.verbose,
        )
        print(result)
        return

    # ── 交互模式 ──
    _run_interactive(
        use_team=args.team,
        max_iterations=args.max_iterations,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
