"""
test_medication_safety — 药物安全测试
重点审查：FORBIDDEN_DOSAGE_PATTERNS 覆盖度、DDI 矩阵、禁忌症检查
"""
import pytest
import re

# 禁止输出的剂量模式
FORBIDDEN_DOSAGE_PATTERNS = [
    r"建议.*服用.*\d+.*片",
    r"每次.*\d+.*mg",
    r"一日.*\d+.*次.*每次",
    r"减量至.*\d+",
    r"增加.*剂量.*\d+",
    r"加倍.*服用",
    r"每次.*\d+.*粒",
    r"每日.*\d+.*mg",
    r"建议.*用量.*\d+",
    r"推荐.*剂量.*\d+",
]

DISCLAIMER = (
    "\n\n【免责声明】以上信息仅供参考，不能替代医师处方和用药指导。"
    "用药前请务必咨询医生或药师，切勿自行调整用药方案。"
)


def _check_no_dosage_advice(text: str) -> bool:
    """检查文本中是否包含具体的剂量建议"""
    for pattern in FORBIDDEN_DOSAGE_PATTERNS:
        if re.search(pattern, text):
            return False
    return True


def _check_has_disclaimer(text: str) -> bool:
    """检查是否包含免责声明"""
    return "免责声明" in text and "咨询" in text


# ── 测试用例 ─────────────────────────────────────────

class TestDosageSafety:
    """剂量安全测试"""

    def test_no_dosage_advice_in_response(self):
        """确保回复中不包含具体剂量建议"""
        responses = [
            "关于阿司匹林的使用，请咨询您的医生。{DISCLAIMER}",
            "华法林是处方药，请遵医嘱使用。{DISCLAIMER}",
            "建议您到医院就诊，由医生评估后决定用药方案。{DISCLAIMER}",
        ]
        for r in responses:
            full = r.format(DISCLAIMER=DISCLAIMER)
            assert _check_no_dosage_advice(full), f"检测到剂量建议: {r}"

    def test_detect_forbidden_dosage_patterns(self):
        """测试禁止模式检测"""
        forbidden_examples = [
            "建议每次服用2片",
            "每次500mg",
            "一日3次每次2片",
            "减量至每日50mg",
            "增加剂量到100mg",
            "加倍服用",
            "每次3粒",
            "每日100mg",
            "建议用量500mg",
            "推荐剂量每次2片",
        ]
        for example in forbidden_examples:
            assert not _check_no_dosage_advice(example), f"未检测到禁止模式: {example}"

    def test_disclaimer_always_present(self):
        """确保免责声明始终存在"""
        test_responses = [
            "阿司匹林是常用的抗血小板药物。" + DISCLAIMER,
            "华法林需要定期监测INR。" + DISCLAIMER,
            "硝酸甘油用于心绞痛急性发作。" + DISCLAIMER,
        ]
        for r in test_responses:
            assert _check_has_disclaimer(r)


class TestDDIMatrix:
    """药物-药物相互作用矩阵测试"""

    DDI_MATRIX = {
        ("华法林", "阿司匹林"): {
            "level": "严重",
            "description": "出血风险叠加，联合使用可能显著增加出血风险",
        },
        ("硝酸甘油", "西地那非"): {
            "level": "禁忌",
            "description": "可导致致命性低血压，绝对禁忌",
        },
        ("氯吡格雷", "奥美拉唑"): {
            "level": "中等",
            "description": "奥美拉唑可降低氯吡格雷活性代谢产物，影响抗血小板效果",
        },
        ("螺内酯", "ACEI"): {
            "level": "中等",
            "description": "高钾血症风险，需监测血钾",
        },
    }

    def test_ddi_warfarin_aspirin(self):
        """华法林+阿司匹林 → 严重出血风险"""
        ddi = self.DDI_MATRIX.get(("华法林", "阿司匹林"))
        assert ddi is not None
        assert ddi["level"] == "严重"
        assert "出血" in ddi["description"]

    def test_ddi_nitroglycerin_sildenafil(self):
        """硝酸甘油+西地那非 → 绝对禁忌"""
        ddi = self.DDI_MATRIX.get(("硝酸甘油", "西地那非"))
        assert ddi is not None
        assert ddi["level"] == "禁忌"

    def test_ddi_all_pairs_have_descriptions(self):
        """所有 DDI 对都有描述"""
        for pair, info in self.DDI_MATRIX.items():
            assert "level" in info
            assert "description" in info
            assert len(info["description"]) > 0


class TestDiseaseDrugContraindication:
    """疾病-药物禁忌测试"""

    CONTRAINDICATIONS = {
        "肾功能不全": {
            "forbidden": ["布洛芬", "双氯芬酸", "NSAIDs"],
            "reason": "NSAIDs可加重肾功能损害",
        },
        "消化性溃疡": {
            "forbidden": ["阿司匹林", "布洛芬"],
            "reason": "可诱发或加重消化道出血",
        },
        "哮喘": {
            "forbidden": ["普萘洛尔", "阿替洛尔"],
            "reason": "β受体阻滞剂可诱发支气管痉挛",
        },
        "痛风": {
            "forbidden": ["氢氯噻嗪", "呋塞米"],
            "reason": "利尿剂可升高尿酸，诱发痛风发作",
        },
    }

    def test_renal_insufficiency_contraindication(self):
        """肾功能不全禁用 NSAIDs"""
        ci = self.CONTRAINDICATIONS["肾功能不全"]
        assert "布洛芬" in ci["forbidden"]

    def test_ulcer_contraindication(self):
        """消化性溃疡禁用阿司匹林"""
        ci = self.CONTRAINDICATIONS["消化性溃疡"]
        assert "阿司匹林" in ci["forbidden"]

    def test_all_contraindications_have_reason(self):
        """所有禁忌都有原因说明"""
        for disease, info in self.CONTRAINDICATIONS.items():
            assert "forbidden" in info
            assert "reason" in info
            assert len(info["reason"]) > 0
