"""Emotion detection service for empathetic responses."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

EMOTION_KEYWORDS = {
    "anxious": ["焦虑", "紧张", "害怕", "担心", "压力大", "睡不着", "失眠", "慌", "怕"],
    "confused": ["迷茫", "不知道", "犹豫", "纠结", "选择困难", "怎么办", "该不该"],
    "frustrated": ["失望", "难过", "伤心", "崩溃", "放弃", "考砸", "没考好", "落榜", "挫败"],
    "excited": ["开心", "兴奋", "期待", "激动", "太好了", "终于"],
}

COMFORT_TEMPLATES = {
    "anxious": "我理解你的焦虑，备考压力确实不小。让我们一步步来看——",
    "confused": "选择确实不容易，让我帮你梳理一下——",
    "frustrated": "我能理解你的心情。每一次经历都是成长的一部分，让我看看能怎么帮到你——",
    "excited": "太棒了！很高兴你有这样积极的状态！",
}


@dataclass
class EmotionResult:
    emotion: str | None  # anxious/confused/frustrated/excited/None
    comfort_prefix: str | None


def detect_emotion(message: str) -> EmotionResult:
    """Detect emotional state from user message using keyword matching."""
    text = message.lower()

    for emotion, keywords in EMOTION_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return EmotionResult(
                    emotion=emotion,
                    comfort_prefix=COMFORT_TEMPLATES.get(emotion),
                )

    return EmotionResult(emotion=None, comfort_prefix=None)
