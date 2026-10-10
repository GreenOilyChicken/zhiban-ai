"""
elderly_agent — 银发康养智能体子包
提供老年人用药指导、护理建议、康复计划、长护险申请等专业服务。

核心组件：
- build_elderly_agent(): 构建单一康养 Agent（惰性初始化）
- build_elderly_team(): 构建 Planner-Executor 团队（4 个专家）
- main(): CLI 入口
"""
from .elderly_agent import build_elderly_agent, SYSTEM_PROMPT
from .elderly_team import build_elderly_team

__all__ = ["build_elderly_agent", "build_elderly_team", "SYSTEM_PROMPT"]
