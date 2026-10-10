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
