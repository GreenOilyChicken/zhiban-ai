"""
main - 文旅智能导览系统 CLI 入口

用法：
    python -m tourism_agent.main                    # 交互模式
    python -m tourism_agent.main --build-kb         # 构建知识库
    python -m tourism_agent.main --build-kb --rebuild  # 重建知识库
    python -m tourism_agent.main --verbose           # 详细日志模式
    python -m tourism_agent.main --team              # 使用团队模式
    python -m tourism_agent.main --query "故宫门票"  # 单次查询

功能：
1. --build-kb: 从知识库文档构建向量库
2. --rebuild: 强制重建（先删除旧库）
3. --verbose: 输出详细日志
4. --team: 使用 Planner-Executor 团队模式
5. --query: 单次查询模式（不进入交互循环）
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import config
from base.model_factory import ModelFactory
from knowledge_base.build_kb import build_knowledge_base


logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool = False):
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _ensure_tourism_docs() -> Path:
    """确保旅游知识库文档目录存在，如无文档则创建示例文档"""
    docs_dir = config.KB_TOURISM_DIR
    docs_dir.mkdir(parents=True, exist_ok=True)

    # 检查是否有文档
    has_docs = any(
        f.suffix.lower() in {".txt", ".md", ".markdown"}
        for f in docs_dir.rglob("*")
        if f.is_file()
    )

    if not has_docs:
        logger.info("旅游知识库文档目录为空，创建示例文档...")
        _create_sample_docs(docs_dir)

    return docs_dir


def _create_sample_docs(docs_dir: Path):
    """创建示例知识库文档"""
    sample_texts = {
        "故宫导览.txt": (
            "故宫，又称紫禁城，位于北京市中心，是明清两代的皇家宫殿。"
            "占地面积72万平方米，建筑面积约15万平方米，"
            "有大小宫殿70多座，房屋9000余间。"
            "故宫于1420年建成，距今已有600多年历史。"
            "1987年被联合国教科文组织列为世界文化遗产。\n"
            "故宫博物院成立于1925年10月10日，"
            "是中国最大的古代文化艺术博物馆。"
            "现有藏品总量186万件/套，其中珍贵文物占93.2%。"
        ),
        "长城导览.txt": (
            "万里长城是中国古代的军事防御工程，"
            "始建于春秋战国时期，后经秦、汉、明等多代修缮扩建。"
            "明长城东起鸭绿江畔虎山，西至甘肃嘉峪关，"
            "总长度约8850公里。北京附近的八达岭长城"
            "是最具代表性的段落，建于明代，"
            "城墙高大坚固，是明长城精华所在。"
            "1987年被列为世界文化遗产。"
        ),
        "兵马俑导览.txt": (
            "秦始皇兵马俑位于陕西省西安市临潼区，"
            "是秦始皇陵的陪葬坑。1974年被发现，"
            "被誉为世界第八大奇迹。三个坑中"
            "埋藏着约8000件与真人真马等大的陶俑陶马，"
            "排成军阵，气势恢宏。1987年被列为世界文化遗产。"
        ),
    }

    for filename, content in sample_texts.items():
        filepath = docs_dir / filename
        filepath.write_text(content, encoding="utf-8")
        logger.info("创建示例文档: %s" % filename)


def _build_kb(rebuild: bool = False):
    """构建旅游知识库向量索引"""
    docs_dir = _ensure_tourism_docs()
    chroma_dir = config.KB_CHROMA_DIR

    if rebuild:
        logger.info("重建知识库（清除旧数据）...")
        # 删除旧的 ChromaDB 目录
        import shutil
        if chroma_dir.exists():
            shutil.rmtree(chroma_dir)
            logger.info("已清除旧向量库: %s" % chroma_dir)
        # 重置向量库缓存
        try:
            from .tools.attraction_guide import _reset_vectordb
            _reset_vectordb()
        except Exception:
            pass

    logger.info("开始构建知识库...")
    logger.info("  文档目录: %s" % docs_dir)
    logger.info("  向量库目录: %s" % chroma_dir)

    embeddings = ModelFactory.get_embeddings()
    vectordb = build_knowledge_base(
        docs_dir=docs_dir,
        collection_name="tourism",
        persist_dir=chroma_dir,
        embeddings=embeddings,
    )

    logger.info("知识库构建完成！")
    return vectordb


def _run_interactive(use_team: bool = False, verbose: bool = False):
    """运行交互式对话"""
    if use_team:
        from .tourism_team import build_tourism_team
        agent = build_tourism_team(verbose=verbose)
        agent_name = "文旅导览团队（Planner-Executor）"
    else:
        from .tourism_agent import build_tourism_agent
        agent = build_tourism_agent(verbose=verbose)
        agent_name = "文旅导览助手"

    chat_history: list = []

    print("=" * 60)
    print("  欢迎使用知伴AI - 文旅智能导览系统")
    print("  模式: %s" % agent_name)
    print("=" * 60)
    print()
    print("  我可以帮您：")
    print("  1. 查询景点信息（开放时间、门票、交通、看点）")
    print("  2. 规划旅游行程（1-3天，含老人出行建议）")
    print("  3. 讲述景点文化故事（历史、建筑、传说、人物）")
    print()
    print("  输入 'quit' 或 'exit' 退出，输入 'reset' 清空对话历史")
    print()

    while True:
        try:
            user_input = input("您> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print("感谢使用，祝您旅途愉快！")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("感谢使用，祝您旅途愉快！")
            break

        if user_input.lower() == "reset":
            chat_history.clear()
            print("对话历史已清空。")
            print()
            continue

        print()
        try:
            result = agent.run(user_input, chat_history=chat_history)
            chat_history.append(("human", user_input))
            chat_history.append(("ai", result))
            # 保留最近10轮
            if len(chat_history) > 20:
                chat_history = chat_history[-20:]

            print("导览助手> %s" % result)
            print()
        except Exception as e:
            logger.error("处理失败: %s" % e, exc_info=verbose)
            print("抱歉，处理您的问题时出现了错误，请稍后重试。")
            print()


def _run_query(query: str, use_team: bool = False, verbose: bool = False):
    """单次查询模式"""
    if use_team:
        from .tourism_team import build_tourism_team
        agent = build_tourism_team(verbose=verbose)
    else:
        from .tourism_agent import build_tourism_agent
        agent = build_tourism_agent(verbose=verbose)

    result = agent.run(query)
    print(result)


def main():
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        description="知伴AI - 文旅智能导览系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python -m tourism_agent.main                           # 交互模式\n"
            "  python -m tourism_agent.main --build-kb                # 构建知识库\n"
            "  python -m tourism_agent.main --build-kb --rebuild      # 重建知识库\n"
            "  python -m tourism_agent.main --query \"故宫门票多少钱\"   # 单次查询\n"
            "  python -m tourism_agent.main --team --verbose           # 团队模式+详细日志\n"
        ),
    )
    parser.add_argument(
        "--build-kb",
        action="store_true",
        help="构建旅游知识库向量索引",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="强制重建知识库（先删除旧数据），需与 --build-kb 一起使用",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出详细日志信息",
    )
    parser.add_argument(
        "--team",
        action="store_true",
        help="使用 Planner-Executor 团队模式（默认使用单一智能体）",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="",
        help="单次查询模式，直接回答问题后退出",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="打印配置信息后退出",
    )

    args = parser.parse_args()

    _setup_logging(verbose=args.verbose)

    # 打印配置
    if args.config:
        config.print_config_summary()
        return

    # 构建知识库
    if args.build_kb:
        _build_kb(rebuild=args.rebuild)
        if not args.query:
            return

    # 单次查询
    if args.query:
        _run_query(args.query, use_team=args.team, verbose=args.verbose)
        return

    # 交互模式
    _run_interactive(use_team=args.team, verbose=args.verbose)


if __name__ == "__main__":
    main()
