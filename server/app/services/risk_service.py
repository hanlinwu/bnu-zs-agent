"""Risk classification service for user questions."""

import logging

logger = logging.getLogger(__name__)

# Keywords that indicate high-risk questions (specific numbers, policies, guarantees)
HIGH_RISK_KEYWORDS = [
    "保证录取", "一定能上", "包过", "内部名额", "走后门", "关系户",
    "最低分数线", "确切分数", "保底", "承诺", "100%",
    "退学费", "违约金", "法律", "投诉", "举报",
]

# Keywords that indicate medium-risk questions (specific data that needs sourcing)
MEDIUM_RISK_KEYWORDS = [
    "分数线", "录取率", "学费", "奖学金金额", "就业率", "薪资",
    "排名", "招生人数", "报录比", "调剂", "复试线",
    "宿舍费", "住宿", "报名时间", "截止日期",
]


def classify_risk(message: str, context: list[dict] | None = None) -> str:
    """Classify question risk level.

    Returns:
        "high" - Only return pre-approved answers or redirect to admissions office
        "medium" - Normal generation but force citation of sources
        "low" - Normal generation
    """
    text = message.lower()

    for kw in HIGH_RISK_KEYWORDS:
        if kw in text:
            return "high"

    for kw in MEDIUM_RISK_KEYWORDS:
        if kw in text:
            return "medium"

    return "low"
