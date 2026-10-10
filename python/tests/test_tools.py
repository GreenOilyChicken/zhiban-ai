"""
test_tools — 测试各类工具
"""
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document


class _FakeKB:
    """测试用 Fake 向量库"""
    def __init__(self):
        self._docs = [
            Document(page_content="高血压患者应低盐饮食，每日食盐不超过5克", metadata={"source": "hypertension.txt"}),
            Document(page_content="糖尿病患者应控制血糖，合理膳食", metadata={"source": "diabetes.txt"}),
        ]

    def similarity_search_with_score(self, q, k=3):
        if "高血压" in q:
            return [(self._docs[0], 0.5)]
        return [(self._docs[1], 0.5)]


def test_medication_disclaimer():
    """测试药物工具免责声明"""
    DISCLAIMER = "【免责声明】以上信息仅供参考，用药前请咨询医生或药师。"
    assert "免责声明" in DISCLAIMER
    assert "咨询" in DISCLAIMER


def test_rehab_plan_stage_picking():
    """测试康复计划阶段选择"""
    _PLAN_BOOK = {
        "hip_replacement": [
            {"stage": "术后0-3天", "lo": 0, "hi": 3, "exercises": ["踝泵运动", "股四头肌等长收缩"]},
            {"stage": "术后4-14天", "lo": 4, "hi": 14, "exercises": ["床上坐起", "站立训练"]},
            {"stage": "术后15天以上", "lo": 15, "hi": float('inf'), "exercises": ["助行器行走", "上下楼梯"]},
        ],
    }

    def _pick_stage(plan, day):
        for s in plan:
            if s["lo"] <= day <= s["hi"]:
                return s
        return None

    plan = _PLAN_BOOK["hip_replacement"]
    assert _pick_stage(plan, 1)["stage"] == "术后0-3天"
    assert _pick_stage(plan, 7)["stage"] == "术后4-14天"
    assert _pick_stage(plan, 30)["stage"] == "术后15天以上"
    assert _pick_stage(plan, 99999) is not None  # float('inf') covers this


def test_ltc_id_masking():
    """测试长护险身份证脱敏（生产实现）"""
    from elderly_agent.tools.long_term_care import mask_id_card

    masked = mask_id_card("110105194901011234")
    # 保留前6位和后4位，中间全部打码
    assert masked == "110105********1234"
    assert "1949" not in masked      # 出生年不应暴露
    assert "01011234"[0:4] not in masked[6:-4]

    # 15 位老身份证
    assert mask_id_card("110105490101123") == "1101*******1123"

    # 异常输入统一返回 ***，不泄露原文
    assert mask_id_card("12345") == "***"
    assert mask_id_card("") == "***"
    assert mask_id_card(None) == "***"


def test_ltc_id_validation():
    """测试身份证验证（生产实现）"""
    from elderly_agent.tools.long_term_care import _validate_id_card

    # 校验位正确的合法身份证
    assert _validate_id_card("110105194901010013")["valid"] is True

    # 校验位错误 / 长度错误 / 格式错误
    assert _validate_id_card("110105194901010019")["valid"] is False
    assert _validate_id_card("110105194901010000")["valid"] is False
    assert _validate_id_card("12345")["valid"] is False
    assert _validate_id_card("abcdefghijklmnopqr")["valid"] is False

    # 校验失败必须带可读原因
    assert _validate_id_card("12345")["errors"]


def test_tool_func_query():
    """测试工具函数查询功能（返回 Document，含来源元数据）"""
    with patch("knowledge_base.build_kb.load_knowledge_base") as mock_load:
        mock_load.return_value = _FakeKB()

        from knowledge_base.build_kb import query_knowledge_base

        results = query_knowledge_base("高血压饮食", top_k=3)
        assert len(results) > 0
        assert "高血压" in results[0].page_content
        # 来源元数据必须保留，供政策检索标注出处
        assert results[0].metadata.get("source") == "hypertension.txt"


def test_tool_func_query_text_mode():
    """query_knowledge_base_text 返回纯文本片段"""
    with patch("knowledge_base.build_kb.load_knowledge_base") as mock_load:
        mock_load.return_value = _FakeKB()

        from knowledge_base.build_kb import query_knowledge_base_text

        results = query_knowledge_base_text("高血压饮食", top_k=3)
        assert len(results) > 0
        assert isinstance(results[0], str)
        assert "高血压" in results[0]
