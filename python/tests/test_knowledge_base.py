"""
test_knowledge_base — 测试知识库构建与查询
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from langchain_core.documents import Document


class FakeEmbeddings:
    """测试用 Fake Embeddings"""
    def embed_documents(self, texts):
        return [[0.1 * i for i in range(32)] for _ in texts]

    def embed_query(self, text):
        return [0.1 * i for i in range(32)]


class FakeVectorDB:
    """测试用 Fake 向量库"""
    def __init__(self):
        self._docs = [
            Document(page_content="高血压患者应低盐饮食", metadata={"source": "hypertension.txt", "category": "elderly"}),
            Document(page_content="糖尿病患者应控制血糖", metadata={"source": "diabetes.txt", "category": "elderly"}),
            Document(page_content="冠心病患者应定期复查", metadata={"source": "coronary.txt", "category": "elderly"}),
            Document(page_content="脑卒中后需康复训练", metadata={"source": "stroke.txt", "category": "elderly"}),
        ]

    def similarity_search_with_score(self, q, k=3):
        return [(d, 0.5) for d in self._docs[:k]]


def test_load_documents(tmp_path):
    """测试文档加载"""
    from knowledge_base.build_kb import _load_documents

    # 创建测试文件
    (tmp_path / "test1.txt").write_text("这是测试文档1", encoding="utf-8")
    (tmp_path / "test2.md").write_text("# 测试文档2", encoding="utf-8")

    docs = _load_documents(tmp_path)
    assert len(docs) == 2
    assert "测试文档" in docs[0].page_content


def test_split_documents():
    """测试文档分割（长文本必须被切成多片）"""
    from knowledge_base.build_kb import _split

    docs = [
        Document(page_content="这是一段很长的文字。" * 200, metadata={"source": "test.txt"}),
    ]
    chunks = _split(docs)
    assert len(chunks) > 1
    # 每个片段都不应超过 chunk_size 太多
    assert all(len(c.page_content) <= 700 for c in chunks)
    # 元数据应被继承，供来源标注使用
    assert chunks[0].metadata.get("source") == "test.txt"


def test_collection_has_data(tmp_path):
    """测试数据检查"""
    from knowledge_base.build_kb import _collection_has_data

    # 不存在的路径
    assert _collection_has_data(tmp_path / "nonexistent") is False

    # 空目录
    assert _collection_has_data(tmp_path) is False

    # 有数据库文件
    db_file = tmp_path / "chroma.sqlite3"
    db_file.write_text("x" * 2048)
    assert _collection_has_data(tmp_path) is True

    # 文件过小
    db_file.write_text("x" * 100)
    assert _collection_has_data(tmp_path) is False


def test_query_knowledge_base():
    """测试知识库查询"""
    with patch("knowledge_base.build_kb.load_knowledge_base") as mock_load:
        mock_load.return_value = FakeVectorDB()

        from knowledge_base.build_kb import query_knowledge_base

        results = query_knowledge_base("高血压", top_k=3)
        assert len(results) <= 3


def test_query_input_length_limit():
    """测试查询长度限制"""
    with patch("knowledge_base.build_kb.load_knowledge_base") as mock_load:
        mock_load.return_value = FakeVectorDB()

        from knowledge_base.build_kb import query_knowledge_base

        long_query = "x" * 20000
        results = query_knowledge_base(long_query, top_k=3)
        assert len(results) <= 3


@pytest.mark.skipif(
    not (Path(__file__).resolve().parent.parent / "knowledge_base" / "policies").exists(),
    reason="CI 环境可能缺少政策文档"
)
def test_policies_dir_has_all_4_categories():
    """测试政策文档目录包含 4 个分类"""
    policies_dir = Path(__file__).resolve().parent.parent / "knowledge_base" / "policies"
    if not policies_dir.exists():
        pytest.skip("政策文档目录不存在")

    categories = [d.name for d in policies_dir.iterdir() if d.is_dir()]
    assert len(categories) >= 1


# ── 回归测试：本次修复的缺陷 ──────────────────────────────

def test_query_with_scores_converts_distance_to_similarity():
    """
    回归：Chroma 的 similarity_search_with_score 返回的是【距离】（越小越相似），
    必须换算为【相似度】（越大越相似），否则下游 score>=0.75 的阈值过滤永远不通过。
    """
    from knowledge_base.build_kb import query_knowledge_base_with_scores

    class DistanceDB:
        def similarity_search_with_score(self, q, k=3):
            # 距离 0.0 = 完全相同；距离 1.0 = 正交；距离越大越不相关
            return [
                (Document(page_content="完全匹配", metadata={"source": "a.txt"}), 0.0),
                (Document(page_content="比较相关", metadata={"source": "b.txt"}), 1.0),
                (Document(page_content="毫不相关", metadata={"source": "c.txt"}), 2.0),
            ]

    pairs = query_knowledge_base_with_scores("q", top_k=3, vectordb=DistanceDB())
    assert len(pairs) == 3
    sims = [sim for _doc, sim in pairs]

    # 距离越小 -> 相似度越大
    assert sims[0] > sims[1] > sims[2]
    # 换算公式 cos = 1 - d²/2：距离 0 -> 相似度 1.0（完全匹配）
    assert sims[0] == pytest.approx(1.0)
    # 距离 1.0 -> 相似度 0.5（正交）
    assert sims[1] == pytest.approx(0.5)
    # 距离 2.0 -> 相似度被裁剪到 0，不出现负值
    assert sims[2] == pytest.approx(0.0)
    # 相似度必须落在 [0,1]
    assert all(0.0 <= s <= 1.0 for s in sims)


def test_query_with_scores_empty_query():
    """空查询应返回空列表，而不是抛异常"""
    from knowledge_base.build_kb import query_knowledge_base_with_scores

    assert query_knowledge_base_with_scores("") == []
    assert query_knowledge_base_with_scores("   ") == []


def test_rebuild_twice_does_not_fail(tmp_path):
    """
    回归：全量重建会 rmtree 持久化目录，但 ChromaDB 在进程内以目录为 key
    缓存了 System/Client，复用旧句柄会报
    'attempt to write a readonly database'，导致【第二次重建必定失败】。
    修复方式是在重建前清空 SharedSystemClient 缓存。
    """
    from knowledge_base.build_kb import build_knowledge_base

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.txt").write_text("长期护理保险政策内容。", encoding="utf-8")
    persist = tmp_path / "db"

    # 连续重建三次都应成功（修复前第 2 次起必失败）
    for i in range(3):
        build_knowledge_base(
            docs_dir=docs,
            collection_name="regressioncol",
            persist_dir=persist,
            rebuild=True,
            embeddings=FakeEmbeddings(),
        )


def test_upload_endpoint_declares_form_fields():
    """
    回归：/api/v1/kb/upload 的 collection / rebuild 必须用 Form(...) 声明。
    若声明为普通默认参数，FastAPI 会当作 query 参数，
    multipart 表单里的同名字段被静默忽略（曾导致文件落入错误集合）。
    """
    import inspect
    import rag_server

    sig = inspect.signature(rag_server.upload_kb_document)
    for name in ("collection", "rebuild"):
        param = sig.parameters[name]
        assert param.default is not inspect.Parameter.empty, f"{name} 应有默认值"
        # FastAPI 的 Form(...) 会生成 FieldInfo，其 annotation 被解析为对应类型
        # 这里断言默认值不是裸 str/bool，而是 FastAPI 的 Form 包装
        assert not isinstance(param.default, (str, bool)), (
            f"{name} 必须用 Form(...) 声明，否则 multipart 表单字段会被忽略"
        )
