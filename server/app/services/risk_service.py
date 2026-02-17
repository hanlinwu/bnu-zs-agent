"""Risk classification service for user questions."""

import logging
import re

from app.services.system_config_service import get_chat_guardrail_config_cached

logger = logging.getLogger(__name__)

_DIGIT_RE = re.compile(r"\d")


def classify_risk(message: str, context: list[dict] | None = None, config: dict | None = None) -> str:
    """Classify question risk level.

    Returns:
        "high" - Only return pre-approved answers or redirect to admissions office
        "medium" - Normal generation but force citation of sources
        "low" - Normal generation
    """
    text = message.lower()
    cfg = config or get_chat_guardrail_config_cached()
    risk_cfg = cfg.get("risk", {})

    high_keywords = [str(kw).lower() for kw in risk_cfg.get("high_keywords", [])]
    medium_keywords = [str(kw).lower() for kw in risk_cfg.get("medium_keywords", [])]
    medium_topics = [str(kw).lower() for kw in risk_cfg.get("medium_topics", [])]
    medium_specific_hints = [str(kw).lower() for kw in risk_cfg.get("medium_specific_hints", [])]

    for kw in high_keywords:
        if kw in text:
            return "high"

    for kw in medium_keywords:
        if kw in text:
            return "medium"

    # Topic + specificity => medium risk (for concrete/key policy questions)
    has_topic = any(kw in text for kw in medium_topics)
    has_specific_hint = any(kw in text for kw in medium_specific_hints) or bool(_DIGIT_RE.search(text))
    if has_topic and has_specific_hint:
        return "medium"

    return "low"
