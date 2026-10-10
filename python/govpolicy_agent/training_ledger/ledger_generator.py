"""
ledger_generator — 季度培训台账 Word 文档生成器
使用 python-docx 生成规范化的季度培训台账文档。

功能：
- 根据 quarter（如 "2026Q1"）自动计算季度日期范围
- 生成封面、培训内容表、参训人员表、签到表
- 表格样式回退（Light Grid Accent 1 → Table Grid）
- 文件名安全化处理
"""
from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import config

logger = logging.getLogger(__name__)


# ── 日期工具 ──────────────────────────────────────────

def _quarter_to_daterange(quarter: str) -> Tuple[date, date]:
    """
    将季度字符串（如 "2026Q1"、"2026-Q1"、"2026/Q1"）转换为日期范围。

    统一计算逻辑：
    - Q1: 01-01 ~ 03-31
    - Q2: 04-01 ~ 06-30
    - Q3: 07-01 ~ 09-30
    - Q4: 10-01 ~ 12-31

    Returns:
        (start_date, end_date)
    Raises:
        ValueError: 季度字符串格式不合法
    """
    quarter = quarter.strip().upper()
    # 兼容 "2026Q1"、"2026-Q1"、"2026/Q1"、"2026 Q1"
    match = re.match(r"^(\d{4})\s*[-/]?\s*Q([1-4])$", quarter)
    if not match:
        raise ValueError(
            f"季度格式不合法: '{quarter}'，期望格式如 '2026Q1' 或 '2026-Q1'"
        )

    year = int(match.group(1))
    q = int(match.group(2))

    start_month = (q - 1) * 3 + 1
    start_date = date(year, start_month, 1)

    # 季度末月
    end_month = q * 3
    if end_month == 12:
        end_date = date(year, 12, 31)
    else:
        # 下个月1号的前一天
        end_date = date(year, end_month + 1, 1) - timedelta(days=1)

    return start_date, end_date


# ── 文件名安全化 ──────────────────────────────────────

def _sanitize_filename(name: str) -> str:
    """
    将字符串安全化为文件名：
    - 移除/替换非法字符（\\ / : * ? " < > |）
    - 压缩连续空格和下划线
    - 空结果回退为 "unknown"

    Returns:
        安全的文件名字符串（不含扩展名）
    """
    if not name or not name.strip():
        return "unknown"

    result = name.strip()
    # 替换路径分隔符和非法字符
    result = re.sub(r'[\\/:*?"<>|]', "_", result)
    # 压缩连续下划线
    result = re.sub(r"_+", "_", result)
    # 压缩连续空格
    result = re.sub(r"\s+", " ", result)
    # 首尾下划线/空格
    result = result.strip("_").strip()

    if not result:
        return "unknown"

    return result


# ── 表格样式辅助 ──────────────────────────────────────

_TABLE_STYLE_PREFERRED = "Light Grid Accent 1"
_TABLE_STYLE_FALLBACK = "Table Grid"


def _apply_table_style(table, style_name: str = _TABLE_STYLE_PREFERRED) -> str:
    """
    给表格应用样式，带回退机制。
    优先使用 style_name，失败时回退到 "Table Grid"。

    Returns:
        实际应用的样式名
    """
    try:
        table.style = style_name
        return style_name
    except Exception as e:
        logger.warning(
            f"表格样式 '{style_name}' 应用失败: {e}，回退到 '{_TABLE_STYLE_FALLBACK}'"
        )
        try:
            table.style = _TABLE_STYLE_FALLBACK
            return _TABLE_STYLE_FALLBACK
        except Exception as e2:
            logger.error(f"回退样式 '{_TABLE_STYLE_FALLBACK}' 也失败: {e2}")
            return ""


# ── LedgerGenerator ───────────────────────────────────

# topics 参数类型：(主题名, 参训人员列表, 培训日期)
_TOPIC_TYPE = Tuple[str, List[str], str]


class LedgerGenerator:
    """
    季度培训台账 Word 文档生成器。

    用法：
        gen = LedgerGenerator()
        path = gen.generate(
            quarter="2026Q1",
            unit_name="XX区政务服务中心",
            topics=[
                ("政策解读培训", ["张三", "李四"], "2026-02-15"),
                ("法规学习", ["王五", "赵六"], "2026-03-10"),
            ],
        )
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or config.LEDGER_OUTPUT_DIR

    # ── 文档构建 ─────────────────────────────────────

    def _create_document(self):
        """创建 Word 文档并设置基本属性"""
        from docx import Document
        from docx.shared import Pt

        doc = Document()

        # 设置默认字体
        style = doc.styles["Normal"]
        font = style.font
        font.name = "宋体"
        font.size = Pt(12)

        return doc

    def _add_cover(self, doc, quarter: str, unit_name: str) -> None:
        """添加封面页"""
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        # 空行
        for _ in range(6):
            doc.add_paragraph("")

        # 标题
        title = doc.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title.add_run(f"{quarter} 季度培训台账")
        run.font.size = Pt(28)
        run.bold = True

        doc.add_paragraph("")

        subtitle = doc.add_paragraph()
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = subtitle.add_run(unit_name)
        run.font.size = Pt(18)

        # 空行填充到下一页
        for _ in range(8):
            doc.add_paragraph("")

        footer_p = doc.add_paragraph()
        footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = footer_p.add_run(f"生成日期：{date.today().strftime('%Y-%m-%d')}")
        run.font.size = Pt(12)

        doc.add_page_break()

    def _add_training_table(
        self,
        doc,
        topics: Sequence[_TOPIC_TYPE],
        quarter: str,
        unit_name: str,
    ) -> None:
        """添加培训内容明细表"""
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        # 标题
        heading = doc.add_paragraph()
        run = heading.add_run("一、培训内容明细")
        run.font.size = Pt(16)
        run.bold = True

        start_date, end_date = _quarter_to_daterange(quarter)
        info_p = doc.add_paragraph()
        info_p.add_run(
            f"统计周期：{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
        ).font.size = Pt(11)

        info_p2 = doc.add_paragraph()
        info_p2.add_run(f"培训单位：{unit_name}").font.size = Pt(11)

        doc.add_paragraph("")

        # 表头
        headers = ["序号", "培训主题", "培训日期", "参训人数", "参训人员", "备注"]
        table = doc.add_table(rows=1, cols=len(headers))

        # 设置表头
        for i, header in enumerate(headers):
            cell = table.rows[0].cells[i]
            cell.text = header
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.bold = True
                    run.font.size = Pt(11)

        # 应用表格样式（带回退）
        _apply_table_style(table)

        # 填充数据行
        for idx, (topic_name, attendees, train_date) in enumerate(topics, 1):
            row = table.add_row()
            row.cells[0].text = str(idx)
            row.cells[1].text = topic_name
            row.cells[2].text = train_date
            row.cells[3].text = str(len(attendees))
            row.cells[4].text = "、".join(attendees) if attendees else ""
            row.cells[5].text = ""

            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(11)

        doc.add_paragraph("")

    def _add_summary_table(
        self,
        doc,
        topics: Sequence[_TOPIC_TYPE],
        quarter: str,
        unit_name: str,
    ) -> None:
        """添加培训汇总统计表"""
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        heading = doc.add_paragraph()
        run = heading.add_run("二、培训汇总统计")
        run.font.size = Pt(16)
        run.bold = True

        doc.add_paragraph("")

        total_sessions = len(topics)
        total_attendees = sum(len(attendees) for _, attendees, _ in topics)
        unique_attendees = set()
        for _, attendees, _ in topics:
            unique_attendees.update(attendees)

        stats_data = [
            ("培训次数", f"{total_sessions} 次"),
            ("累计参训人次", f"{total_attendees} 人次"),
            ("参训人员数", f"{len(unique_attendees)} 人"),
            ("培训单位", unit_name),
        ]

        table = doc.add_table(rows=len(stats_data), cols=2)

        for i, (label, value) in enumerate(stats_data):
            row = table.rows[i]
            row.cells[0].text = label
            row.cells[1].text = value

            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(11)
                    if cell is row.cells[0]:
                        for run in paragraph.runs:
                            run.bold = True

        _apply_table_style(table)

        doc.add_paragraph("")

    def _add_sign_in_table(
        self,
        doc,
        topics: Sequence[_TOPIC_TYPE],
    ) -> None:
        """添加签到表"""
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        heading = doc.add_paragraph()
        run = heading.add_run("三、签到表")
        run.font.size = Pt(16)
        run.bold = True

        doc.add_paragraph("")

        for idx, (topic_name, attendees, train_date) in enumerate(topics, 1):
            # 子标题
            sub = doc.add_paragraph()
            run = sub.add_run(f"培训 {idx}：{topic_name}（{train_date}）")
            run.font.size = Pt(13)
            run.bold = True

            # 签到表
            headers = ["序号", "姓名", "签到状态", "备注"]
            table = doc.add_table(rows=1, cols=len(headers))

            for i, header in enumerate(headers):
                cell = table.rows[0].cells[i]
                cell.text = header
                for paragraph in cell.paragraphs:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for run in paragraph.runs:
                        run.bold = True
                        run.font.size = Pt(11)

            _apply_table_style(table)

            for person_idx, person in enumerate(attendees, 1):
                row = table.add_row()
                row.cells[0].text = str(person_idx)
                row.cells[1].text = person
                row.cells[2].text = "□ 已签到"
                row.cells[3].text = ""

            doc.add_paragraph("")

    def _add_footer_note(self, doc) -> None:
        """添加尾部说明"""
        from docx.shared import Pt

        doc.add_page_break()

        heading = doc.add_paragraph()
        run = heading.add_run("四、说明")
        run.font.size = Pt(16)
        run.bold = True

        notes = [
            "1. 本台账由政务政策智能体辅助生成，仅供培训管理参考。",
            "2. 签到状态请在实际培训时手动勾选确认。",
            "3. 如需修改培训内容，请联系相关负责人员。",
            "4. 本台账应妥善保管，作为培训档案存档。",
        ]

        for note in notes:
            p = doc.add_paragraph()
            p.add_run(note).font.size = Pt(11)

    # ── 主入口 ───────────────────────────────────────

    def generate(
        self,
        quarter: str,
        unit_name: str = "",
        topics: Optional[List[_TOPIC_TYPE]] = None,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        生成季度培训台账 Word 文档。

        Args:
            quarter: 季度字符串，如 "2026Q1" 或 "2026-Q1"
            unit_name: 培训单位名称
            topics: 培训主题列表，每项为 (主题名, 参训人员列表, 培训日期)
            output_path: 输出路径（不含则自动生成）

        Returns:
            生成的文件路径

        Raises:
            ValueError: quarter 格式不合法
            RuntimeError: 文档生成失败
        """
        topics = list(topics) if topics else []

        # 验证季度格式
        start_date, end_date = _quarter_to_daterange(quarter)
        quarter_clean = quarter.strip().upper().replace("-", "").replace("/", "").replace(" ", "")
        unit_clean = _sanitize_filename(unit_name) if unit_name else "unknown"

        # 确定输出路径
        if output_path is None:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{quarter_clean}_{unit_clean}_培训台账.docx"
            output_path = self.output_dir / filename

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            doc = self._create_document()

            # 封面
            self._add_cover(doc, quarter_clean, unit_name or "未指定单位")

            # 培训内容明细表
            self._add_training_table(doc, topics, quarter, unit_name or "未指定单位")

            # 培训汇总统计表
            self._add_summary_table(doc, topics, quarter, unit_name or "未指定单位")

            # 签到表
            self._add_sign_in_table(doc, topics)

            # 尾部说明
            self._add_footer_note(doc)

            doc.save(str(output_path))
            logger.info(f"培训台账已生成: {output_path}")

        except Exception as e:
            logger.error(f"生成培训台账失败: {e}")
            raise RuntimeError(f"生成培训台账失败: {e}") from e

        return output_path
