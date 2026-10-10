"""
elderly_agent.tools — 银发康养工具包
导出四个核心工具的 Tool 工厂函数。
"""
from .medication_guide import build_medication_tool
from .care_advice import build_care_advice_tool
from .rehab_plan import build_rehab_plan_tool
from .long_term_care import build_long_term_care_tool

__all__ = [
    "build_medication_tool",
    "build_care_advice_tool",
    "build_rehab_plan_tool",
    "build_long_term_care_tool",
]
