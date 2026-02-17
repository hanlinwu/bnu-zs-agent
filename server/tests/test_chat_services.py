"""Tests for risk, emotion, and calendar services."""

from app.services.risk_service import classify_risk
from app.services.emotion_service import detect_emotion
from app.services.calendar_service import _get_default_period


def test_high_risk_classification():
    assert classify_risk("你能保证录取吗") == "high"
    assert classify_risk("有没有内部名额") == "high"


def test_medium_risk_classification():
    assert classify_risk("今年分数线是多少") == "medium"
    assert classify_risk("学费多少钱") == "medium"


def test_low_risk_classification():
    assert classify_risk("心理学专业怎么样") == "low"
    assert classify_risk("校园环境好吗") == "low"
    assert classify_risk("你好") == "low"


def test_medium_risk_specific_key_question():
    assert classify_risk("研究生招生报名截止时间是什么时候") == "medium"
    assert classify_risk("国际生申请需要什么材料") == "medium"


def test_emotion_anxious():
    result = detect_emotion("我好焦虑啊，压力大")
    assert result.emotion == "anxious"
    assert result.comfort_prefix is not None


def test_emotion_confused():
    result = detect_emotion("我很迷茫不知道选什么专业")
    assert result.emotion == "confused"


def test_emotion_frustrated():
    result = detect_emotion("我考砸了好难过")
    assert result.emotion == "frustrated"


def test_emotion_none():
    result = detect_emotion("请问心理学专业课程有哪些")
    assert result.emotion is None
    assert result.comfort_prefix is None


def test_default_period_mapping():
    assert _get_default_period(3) == "preparation"
    assert _get_default_period(6) == "application"
    assert _get_default_period(8) == "admission"
    assert _get_default_period(11) == "normal"
