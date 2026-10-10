"""
route_planner - 路线规划工具

功能：
1. 支持一日、两日、三日行程规划
2. 按上午、下午、晚间分段安排
3. 包含景点间交通方式
4. 考虑老人体力，合理安排节奏
5. 适老化的语言风格
"""
from __future__ import annotations

import logging
from typing import Optional

from base.agent_framework import Tool

logger = logging.getLogger(__name__)

# ── 城市景点分组 ────────────────────────────────────────

CITY_ATTRACTIONS: dict[str, dict] = {
    "北京": {
        "keywords": ["北京", "beijing", "北平"],
        "full_day": ["故宫", "天安门", "景山公园"],
        "half_day": ["颐和园", "天坛", "长城（八达岭）", "南锣鼓巷", "什刹海"],
        "evening": ["王府井步行街", "前门大街", "后海酒吧街"],
        "transit": "地铁覆盖主要景点，公交也很方便。建议办一张交通卡。",
    },
    "西安": {
        "keywords": ["西安", "xian", "长安"],
        "full_day": ["兵马俑", "秦始皇陵", "华清宫"],
        "half_day": ["大雁塔", "古城墙", "陕西历史博物馆", "回民街", "钟楼鼓楼"],
        "evening": ["大唐不夜城", "回民街美食街", "永兴坊"],
        "transit": "地铁2号线和3号线覆盖主要景点。兵马俑需乘游5路公交约1小时。",
    },
    "杭州": {
        "keywords": ["杭州", "hangzhou"],
        "full_day": ["西湖环湖游（苏堤-断桥-三潭印月）", "灵隐寺-飞来峰"],
        "half_day": ["雷峰塔", "西溪湿地", "河坊街", "龙井茶园"],
        "evening": ["西湖音乐喷泉", "南宋御街", "武林夜市"],
        "transit": "地铁1号线到龙翔桥站近西湖。景区内有电瓶车和游船。",
    },
    "成都": {
        "keywords": ["成都", "chengdu"],
        "full_day": ["都江堰-青城山", "大熊猫繁育研究基地"],
        "half_day": ["武侯祠", "锦里", "杜甫草堂", "宽窄巷子", "人民公园"],
        "evening": ["春熙路", "太古里", "锦里夜游"],
        "transit": "地铁覆盖市区景点。都江堰可乘城际铁路约30分钟。",
    },
    "苏州": {
        "keywords": ["苏州", "suzhou"],
        "full_day": ["拙政园-狮子林-苏州博物馆", "周庄古镇"],
        "half_day": ["留园", "虎丘", "平江路", "山塘街", "寒山寺"],
        "evening": ["山塘街夜景", "网师园夜游", "金鸡湖"],
        "transit": "地铁4号线到北寺塔站近拙政园。古城内可步行或乘公交。",
    },
    "桂林": {
        "keywords": ["桂林", "guilin", "阳朔"],
        "full_day": ["漓江游船（桂林-阳朔）", "阳朔十里画廊"],
        "half_day": ["象鼻山", "两江四湖", "龙脊梯田", "遇龙河"],
        "evening": ["两江四湖夜游", "阳朔西街", "印象刘三姐"],
        "transit": "漓江游船需到码头乘船。到阳朔大巴约1.5小时。",
    },
    "南京": {
        "keywords": ["南京", "nanjing", "金陵"],
        "full_day": ["中山陵-明孝陵-灵谷寺", "夫子庙-秦淮河"],
        "half_day": ["总统府", "南京博物院", "玄武湖", "鸡鸣寺"],
        "evening": ["夫子庙秦淮河夜游", "老门东", "1912街区"],
        "transit": "地铁2号线到苜蓿园站近中山陵。公交覆盖各大景点。",
    },
    "上海": {
        "keywords": ["上海", "shanghai", "沪"],
        "full_day": ["外滩-南京路-豫园", "迪士尼乐园"],
        "half_day": ["东方明珠", "上海博物馆", "田子坊", "新天地", "朱家角古镇"],
        "evening": ["外滩夜景", "陆家嘴", "武康路"],
        "transit": "地铁覆盖全市。2号线到南京东路站近外滩。",
    },
    "丽江": {
        "keywords": ["丽江", "lijiang"],
        "full_day": ["玉龙雪山", "拉市海茶马古道"],
        "half_day": ["丽江古城", "束河古镇", "黑龙潭", "木府"],
        "evening": ["古城酒吧街", "四方街夜景"],
        "transit": "古城内步行。到玉龙雪山约1小时车程，建议包车或参团。",
    },
    "厦门": {
        "keywords": ["厦门", "xiamen", "鼓浪屿"],
        "full_day": ["鼓浪屿全岛游", "南普陀-厦门大学"],
        "half_day": ["曾厝垵", "环岛路", "集美学村", "中山路步行街"],
        "evening": ["中山路夜市", "环岛路夜景", "筼筜湖"],
        "transit": "公交和BRT覆盖全城。到鼓浪屿需乘轮渡。",
    },
    "重庆": {
        "keywords": ["重庆", "chongqing"],
        "full_day": ["武隆天生三桥", "大足石刻"],
        "half_day": ["洪崖洞", "磁器口古镇", "长江索道", "解放碑"],
        "evening": ["洪崖洞夜景", "南山一棵树观景台", "两江夜游"],
        "transit": "轻轨覆盖主要景点。地形起伏大，建议少步行多乘车。",
    },
    "拉萨": {
        "keywords": ["拉萨", "lhasa", "西藏"],
        "full_day": ["布达拉宫-大昭寺-八廓街", "纳木错"],
        "half_day": ["罗布林卡", "色拉寺", "哲蚌寺", "西藏博物馆"],
        "evening": ["八廓街转经", "布达拉宫广场夜景"],
        "transit": "市内公交和出租车方便。海拔高，注意休息。",
    },
}


def _match_city(city_or_area: str) -> Optional[dict]:
    """匹配城市信息"""
    query = city_or_area.strip().lower()
    for city_info in CITY_ATTRACTIONS.values():
        for kw in city_info["keywords"]:
            if kw.lower() in query or query in kw.lower():
                return city_info
    return None


def _build_day_plan(
    day_num: int,
    city_info: dict,
    total_days: int,
) -> str:
    """构建一天的行程计划"""
    full_day = city_info.get("full_day", [])
    half_day = city_info.get("half_day", [])
    evening = city_info.get("evening", [])

    lines = []
    lines.append("  第%d天：" % day_num)
    lines.append("")

    # 上午：选一个主要景点
    morning_idx = (day_num - 1) % len(full_day) if full_day else 0
    morning = full_day[morning_idx] if full_day else (half_day[0] if half_day else "自由活动")
    lines.append("  上午（8:30-12:00）：")
    lines.append("    游览【%s】" % morning)
    lines.append("    建议早上早点出发，避开人流高峰，体力也更好。")
    lines.append("    中午在附近用午餐，注意补充水分。")
    lines.append("")

    # 下午：选一个半日景点
    afternoon_idx = (day_num - 1) % len(half_day) if half_day else 0
    afternoon = half_day[afternoon_idx] if half_day else "自由活动"
    lines.append("  下午（14:00-17:00）：")
    lines.append("    游览【%s】" % afternoon)
    lines.append("    午休后再出门，下午阳光没那么强烈。")
    lines.append("    游览节奏放慢，注意适当在长椅或阴凉处休息。")
    lines.append("")

    # 晚间：选一个晚间活动
    evening_idx = (day_num - 1) % len(evening) if evening else 0
    evening_act = evening[evening_idx] if evening else "自由活动"
    lines.append("  晚间（18:30-21:00）：")
    lines.append("    【%s】" % evening_act)
    lines.append("    晚上可以散步赏夜景，品尝当地美食。")
    lines.append("    注意保暖，晚上气温会降低。")
    lines.append("    如感到疲劳，也可以早回酒店休息。")

    return "\n".join(lines)


def _build_itinerary(
    city_info: dict,
    days: int,
    attractions: Optional[str] = None,
) -> str:
    """构建完整行程"""
    city_name = ""
    for name, info in CITY_ATTRACTIONS.items():
        if info is city_info:
            city_name = name
            break

    lines = []
    lines.append("=" * 50)
    lines.append("%s%d日行程推荐" % (city_name, days))
    lines.append("=" * 50)
    lines.append("")

    # 总体提示
    lines.append("【行程总览】")
    lines.append("适合人群：中老年游客")
    lines.append("游览节奏：上午1个主要景点 + 下午1个景点 + 晚间自由活动")
    lines.append("交通信息：%s" % city_info.get("transit", "建议打车或乘公交"))
    lines.append("")

    # 老人出行总提醒
    lines.append("【老人出行温馨提示】")
    lines.append("1. 随身携带身份证（65岁以上可享门票优惠或免费）")
    lines.append("2. 穿舒适的防滑鞋，带一件薄外套防温差")
    lines.append("3. 带好常用药品（降压药、速效救心丸等）")
    lines.append("4. 每个景点之间安排休息时间，不要赶路")
    lines.append("5. 中午适当午休，保持充足体力")
    lines.append("6. 多喝水，注意防晒")
    lines.append("")

    # 每日行程
    for day in range(1, days + 1):
        lines.append("-" * 40)
        lines.append(_build_day_plan(day, city_info, days))
        lines.append("")

    # 如果有指定景点，补充说明
    if attractions:
        lines.append("【补充说明】")
        lines.append("您特别提到了：%s" % attractions)
        lines.append("建议将以上景点优先安排到行程中，可适当调整每日游览顺序。")
        lines.append("如需调整，请告诉我您的具体需求，我可以重新规划。")
        lines.append("")

    lines.append("=" * 50)
    lines.append("祝您旅途愉快，注意安全！")
    lines.append("=" * 50)

    return "\n".join(lines)


# ── 工具函数 ────────────────────────────────────────────

def route_planner(city: str, days: int = 1, attractions: str = "") -> str:
    """
    规划多日旅游行程

    参数：
        city: 目的地城市（如北京、西安、杭州等）
        days: 行程天数（1-3天）
        attractions: 特别想去的景点（可选）
    """
    if not city or not city.strip():
        return "请告诉我您想去哪个城市旅游，我可以为您规划行程。"

    city = city.strip()
    days = max(1, min(3, days))
    logger.info("路线规划: city=%s, days=%d" % (city, days))

    city_info = _match_city(city)
    if city_info is None:
        supported = "、".join(CITY_ATTRACTIONS.keys())
        return (
            "抱歉，目前暂不支持%s的自动行程规划。\n\n"
            "目前支持的城市有：%s\n\n"
            "如果您要去的城市不在列表中，请告诉我您的具体需求"
            "（想去哪些景点、几天时间），我可以给出一般性建议。\n\n"
            "通用建议：\n"
            "1. 每天安排2个景点为宜，上午下午各一个\n"
            "2. 晚上可以选择逛步行街或欣赏夜景\n"
            "3. 老人出行建议每天午休，不要安排太满\n"
            "4. 提前查好交通路线，选择最方便的方式" % (city, supported)
        )

    return _build_itinerary(city_info, days, attractions if attractions else None)


# ── Tool 包装 ───────────────────────────────────────────

def create_route_planner_tool() -> Tool:
    """创建路线规划工具"""
    return Tool(
        name="route_planner",
        description=(
            "规划多日旅游行程，支持1-3天行程。"
            "按上午、下午、晚间分段安排景点，包含景点间交通方式。"
            "适用于用户询问行程规划、旅游路线、几天怎么玩等问题时。"
            "参数 city 为目的地城市，days 为行程天数，"
            "attractions 为特别想去的景点（可选）。"
        ),
        func=route_planner,
        param_descriptions={
            "city": {
                "description": "目的地城市，如北京、西安、杭州、成都等",
                "required": True,
            },
            "days": {
                "description": "行程天数，1-3天，默认1天",
                "required": False,
            },
            "attractions": {
                "description": "特别想去的景点名称，多个景点用逗号分隔（可选）",
                "required": False,
            },
        },
    )
