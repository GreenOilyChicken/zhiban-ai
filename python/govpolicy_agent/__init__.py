"""
govpolicy_agent — 政务政策智能体
基于知伴AI框架，提供政策检索、法规解读、办事流程咨询与季度培训台账生成。
"""
from .government_agent import build_government_agent
from .government_team import build_government_team

__all__ = ["build_government_agent", "build_government_team"]
