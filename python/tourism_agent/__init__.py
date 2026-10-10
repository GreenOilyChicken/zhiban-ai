"""
tourism_agent - 文旅智能导览系统

知伴AI的文旅导览子系统，提供：
1. 景点导览：查询中国主要景点的详细信息
2. 路线规划：多日行程规划与推荐
3. 文化故事：历史景点的文化背景和典故

核心组件：
- build_tourism_agent(): 构建单一导览智能体（含全部工具）
- build_tourism_team(): 构建 Planner-Executor 团队（按专长路由）
"""
from .tourism_agent import build_tourism_agent, TourismAgent
from .tourism_team import build_tourism_team, TourismTeam

__all__ = [
    "build_tourism_agent",
    "TourismAgent",
    "build_tourism_team",
    "TourismTeam",
]
