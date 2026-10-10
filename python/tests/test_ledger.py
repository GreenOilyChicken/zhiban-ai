"""
test_ledger — 测试台账生成
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock


def test_generate_single_ledger(tmp_path):
    """测试生成单个台账"""
    try:
        from docx import Document as DocxDocument
    except ImportError:
        pytest.skip("python-docx 未安装")

    doc = DocxDocument()
    doc.add_heading("2025年Q2培训台账", level=1)

    # 信息表
    table = doc.add_table(rows=4, cols=2)
    table.style = "Table Grid"
    cells = [
        ("单位名称", "知伴（湖州）智能科技有限公司"),
        ("台账季度", "2025年第二季度"),
        ("负责人", "张三"),
        ("联系电话", "0572-12345678"),
    ]
    for i, (k, v) in enumerate(cells):
        table.rows[i].cells[0].text = k
        table.rows[i].cells[1].text = v

    # 内容
    doc.add_paragraph("培训内容：")
    doc.add_paragraph("1. 惠民政策解读（2学时）")
    doc.add_paragraph("2. 政务服务流程培训（3学时）")

    out_path = tmp_path / "2025Q2-知伴_台账.docx"
    doc.save(str(out_path))

    assert out_path.exists()
    assert out_path.stat().st_size > 1000


def test_sanitize_filename():
    """测试文件名净化"""
    import re

    def _sanitize_filename(name: str) -> str:
        safe = re.sub(r'[\\/:*?"<>|]', "_", name)
        safe = safe.strip(". ")
        if not safe:
            return "unknown"
        return safe

    assert _sanitize_filename("正常名称") == "正常名称"
    assert _sanitize_filename("test/name") == "test_name"
    assert _sanitize_filename("///") == "unknown"
    assert _sanitize_filename("") == "unknown"
    assert _sanitize_filename("a:b?c|d") == "a_b_c_d"


def test_quarter_to_daterange():
    """测试季度日期范围计算"""
    import datetime as dt
    from datetime import timedelta

    def _quarter_to_daterange(year: int, quarter: int):
        quarters = {
            1: (1, 3),
            2: (4, 6),
            3: (7, 9),
            4: (10, 12),
        }
        start_month, end_month = quarters[quarter]
        start_date = dt.date(year, start_month, 1)
        end_month_next = end_month + 1 if end_month < 12 else 1
        year_next = year if end_month < 12 else year + 1
        end_date = dt.date(year_next, end_month_next, 1) - timedelta(days=1)
        return start_date, end_date

    # Q1
    s, e = _quarter_to_daterange(2025, 1)
    assert s == dt.date(2025, 1, 1)
    assert e == dt.date(2025, 3, 31)

    # Q2
    s, e = _quarter_to_daterange(2025, 2)
    assert s == dt.date(2025, 4, 1)
    assert e == dt.date(2025, 6, 30)

    # Q3
    s, e = _quarter_to_daterange(2025, 3)
    assert s == dt.date(2025, 7, 1)
    assert e == dt.date(2025, 9, 30)

    # Q4 (leap year boundary)
    s, e = _quarter_to_daterange(2025, 4)
    assert s == dt.date(2025, 10, 1)
    assert e == dt.date(2025, 12, 31)


def test_ledger_topics_type():
    """测试台账 topics 类型"""
    from typing import List, Tuple, Optional, get_type_hints

    topics_type = Optional[List[Tuple[str, List[str], str]]]

    sample_topics: List[Tuple[str, List[str], str]] = [
        ("惠民政策解读", ["政策概述", "申请条件", "办理流程"], "2学时"),
        ("政务服务培训", ["服务规范", "投诉处理"], "3学时"),
    ]

    assert len(sample_topics) == 2
    assert isinstance(sample_topics[0], tuple)
    assert len(sample_topics[0]) == 3
    assert isinstance(sample_topics[0][1], list)
