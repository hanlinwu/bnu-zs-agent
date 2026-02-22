"""Unit tests for chat decision stage (risk + tool routing)."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

SERVER_DIR = Path(__file__).resolve().parents[1]


def _make_module(name: str):
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m


def _load_module(name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(name, str(file_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _setup_stubs():
    # sqlalchemy stubs
    _make_module("sqlalchemy")
    sa = sys.modules["sqlalchemy"]
    sa.select = lambda *_a, **_kw: None
    sa.and_ = lambda *_a, **_kw: None
    _make_module("sqlalchemy.ext")
    sa_async = _make_module("sqlalchemy.ext.asyncio")

    class AsyncSession:
        pass

    sa_async.AsyncSession = AsyncSession

    # app package
    _make_module("app")
    _make_module("app.models")
    _make_module("app.services")

    # app.models.*
    app_models_user = _make_module("app.models.user")
    app_models_conv = _make_module("app.models.conversation")
    app_models_msg = _make_module("app.models.message")

    class User:
        pass

    class Conversation:
        id = "conv-id"

    class Message:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    app_models_user.User = User
    app_models_conv.Conversation = Conversation
    app_models_msg.Message = Message

    # service stubs
    svc_sensitive = _make_module("app.services.sensitive_service")
    svc_sensitive.check_sensitive = AsyncMock()

    svc_risk = _make_module("app.services.risk_service")
    svc_risk.classify_risk = lambda *_a, **_kw: "low"

    svc_emotion = _make_module("app.services.emotion_service")

    class _Emotion:
        emotion = None
        comfort_prefix = None

    svc_emotion.detect_emotion = lambda *_a, **_kw: _Emotion()

    svc_calendar = _make_module("app.services.calendar_service")
    svc_calendar.get_current_tone = AsyncMock(return_value={"system_hint": ""})
    svc_calendar.get_current_admission_context = AsyncMock(
        return_value={
            "year": 2026,
            "stage_name": "报名期",
            "stage_key": "application",
            "start_date": None,
            "end_date": None,
            "tone_config": {"system_hint": ""},
            "additional_prompt": "",
        }
    )

    svc_knowledge = _make_module("app.services.knowledge_service")
    svc_knowledge.search = AsyncMock(return_value=[])
    svc_knowledge.format_sources_for_prompt = lambda *_a, **_kw: ""
    svc_knowledge.format_sources_for_citation = lambda *_a, **_kw: []

    svc_system_cfg = _make_module("app.services.system_config_service")
    svc_system_cfg.get_chat_guardrail_config_cached = lambda: {}
    svc_system_cfg.get_system_basic_config_cached = lambda: {"system_name": "京师小智"}

    svc_llm = _make_module("app.services.llm_service")

    class _Router:
        async def decision_chat(self, *_a, **_kw):
            return '{"risk_level":"low","tools":[],"search_query":"x","reason":"ok"}'

    svc_llm.llm_router = _Router()

    svc_media = _make_module("app.services.media_match_service")
    svc_media.match_media_for_question = AsyncMock(return_value=[])

    svc_tavily = _make_module("app.services.tavily_service")
    svc_tavily.search = AsyncMock(return_value={"results": []})

    svc_web_cfg = _make_module("app.services.web_search_config_service")
    svc_web_cfg.get_config = AsyncMock(return_value={"enabled": False})
    svc_web_cfg.get_api_key = lambda: ""
    svc_web_cfg.is_enabled = lambda: False


_setup_stubs()
_chat = _load_module("app.services.chat_service", SERVER_DIR / "app" / "services" / "chat_service.py")


class _FakeDB:
    def __init__(self):
        self.added = []
        self.commits = 0

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1


class ChatDecisionUnitTests(unittest.IsolatedAsyncioTestCase):
    async def test_decision_json_and_tool_whitelist(self):
        fake_json = (
            '{"risk_level":"medium","tools":["knowledge_search","web_search","evil_tool"],'
            '"search_query":"2026 招生简章","reason":"需要检索"}'
        )
        with patch.object(_chat, "classify_risk", return_value="low"):
            with patch.object(_chat.llm_router, "decision_chat", new=AsyncMock(return_value=fake_json)):
                result = await _chat._decide_risk_and_tools("问下简章", {})

        self.assertEqual(result["risk_level"], "medium")
        self.assertEqual(result["search_query"], "2026 招生简章")
        self.assertEqual(result["tools"], ["knowledge_search", "web_search"])

    async def test_decision_fallback_when_invalid_json(self):
        with patch.object(_chat, "classify_risk", return_value="medium"):
            with patch.object(_chat.llm_router, "decision_chat", new=AsyncMock(return_value="not-json")):
                result = await _chat._decide_risk_and_tools("学费多少", {})

        self.assertEqual(result["risk_level"], "medium")
        self.assertEqual(result["tools"], ["knowledge_search"])

    async def test_high_risk_forces_no_tools(self):
        fake_json = '{"risk_level":"high","tools":["knowledge_search","web_search"],"search_query":"x"}'
        with patch.object(_chat, "classify_risk", return_value="low"):
            with patch.object(_chat.llm_router, "decision_chat", new=AsyncMock(return_value=fake_json)):
                result = await _chat._decide_risk_and_tools("保证录取吗", {})

        self.assertEqual(result["risk_level"], "high")
        self.assertEqual(result["tools"], [])

    async def test_sensitive_block_short_circuits_models_and_tools(self):
        filter_result = types.SimpleNamespace(
            action="block",
            highest_level="block",
            matched_words=["走后门"],
            message="命中拦截词",
        )
        user = _chat.User()
        conv = _chat.Conversation()
        db = _FakeDB()

        with patch.object(_chat, "check_sensitive", new=AsyncMock(return_value=filter_result)):
            mocked_decision = AsyncMock(return_value='{"risk_level":"low","tools":[],"search_query":"x"}')
            with patch.object(_chat.llm_router, "decision_chat", new=mocked_decision):
                events = [event async for event in _chat.process_message(user, conv, "测试问题", None, db)]

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].get("type"), "sensitive_block")
        self.assertEqual(events[0].get("content"), "命中拦截词")
        self.assertEqual(db.commits, 1)
        mocked_decision.assert_not_called()


if __name__ == "__main__":
    unittest.main()
