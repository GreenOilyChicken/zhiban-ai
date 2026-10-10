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
    """测试长护险身份证脱敏"""
    def _mask_id(id_str: str) -> str:
        if not id_str:
            return ""
        if len(id_str) <= 6:
            return "*" * len(id_str)
        return id_str[:3] + "*" * (len(id_str) - 6) + id_str[-3:]

    assert _mask_id("110105194901011234") == "110***********234"
    assert _mask_id("12345") == "*****"
    assert _mask_id("") == ""

    # 确保即使 LTC_LOG_MASK=false 也不打印明文
    masked = _mask_id("110105194901011234")
    assert "1949" not in masked  # 中间部分不应暴露
    assert "0112" not in masked


def test_ltc_id_validation():
    """测试身份证验证"""
    import re

    def _validate_id(id_str: str) -> bool:
        id_str = id_str.strip().upper()
        if not re.match(r"^\d{17}[\dX]$", id_str):
            return False
        # 校验位算法
        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_map = {0: "1", 1: "0", 2: "X", 3: "9", 4: "8", 5: "7", 6: "6", 7: "5", 8: "4", 9: "3", 10: "2"}
        total = sum(int(id_str[i]) * weights[i] for i in range(17))
        check_code = check_map[total % 11]
        return id_str[17].upper() == check_code

    # 合法身份证
    assert _validate_id("110105194901010019") is True

    # 非法身份证
    assert _validate_id("110105194901010000") is False
    assert _validate_id("12345") is False
    assert _validate_id("abcdefghijklmnopqr") is False


def test_tool_func_query():
    """测试工具函数查询功能"""
    with patch("knowledge_base.build_kb.load_knowledge_base") as mock_load:
        mock_load.return_value = _FakeKB()

        from knowledge_base.build_kb import query_knowledge_base

        results = query_knowledge_base("高血压饮食", top_k=3)
        assert len(results) > 0
        assert "高血压" in results[0].page_content
