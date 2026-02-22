"""Unit tests for the Tavily-based admin web search API."""

import importlib.util
import sys
import types
import unittest
import uuid
from copy import deepcopy
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


# ── Stubs ──────────────────────────────────────────────────────

class _FakeDB:
    """Minimal async DB session stub."""

    def __init__(self):
        self.commits = 0

    async def execute(self, _query):
        return _ExecuteResult()

    def add(self, _obj):
        pass

    async def commit(self):
        self.commits += 1


class _ExecuteResult:
    def scalar_one_or_none(self):
        return None


DEFAULT_CONFIG = {
    "enabled": True,
    "api_key": "tvly-test-key-12345",
    "search_depth": "basic",
    "max_results": 10,
    "include_domains": [],
    "exclude_domains": [],
    "include_answer": False,
    "include_raw_content": False,
    "topic": "general",
    "country": "",
    "time_range": "",
    "chunks_per_source": 3,
    "include_images": False,
}


def _setup_stubs():
    """Set up all stubs needed before loading app modules."""
    # ── FastAPI stubs ──
    fastapi = _make_module("fastapi")

    class APIRouter:
        def get(self, *_a, **_kw):
            return lambda fn: fn

        def post(self, *_a, **_kw):
            return lambda fn: fn

        def put(self, *_a, **_kw):
            return lambda fn: fn

        def delete(self, *_a, **_kw):
            return lambda fn: fn

    fastapi.APIRouter = APIRouter
    fastapi.Depends = lambda x: x
    fastapi.Query = lambda default=None, **_kw: default

    # ── Pydantic stubs ──
    pydantic = _make_module("pydantic")

    class _Field:
        def __init__(self, *_a, **_kw):
            pass

    class BaseModel:
        def __init_subclass__(cls, **_kw):
            pass

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    pydantic.BaseModel = BaseModel
    pydantic.Field = _Field

    # ── SQLAlchemy stubs ──
    sqlalchemy = _make_module("sqlalchemy")
    sqlalchemy.select = lambda model: None
    _make_module("sqlalchemy.ext")
    sa_asyncio = _make_module("sqlalchemy.ext.asyncio")

    class AsyncSession:
        pass

    sa_asyncio.AsyncSession = AsyncSession

    # ── httpx stub ──
    httpx = _make_module("httpx")

    class HTTPStatusError(Exception):
        def __init__(self, *args, response=None, request=None, **kwargs):
            super().__init__(*args)
            self.response = response
            self.request = request

    class AsyncClient:
        def __init__(self, **_kw):
            pass

        async def post(self, url, json=None):
            pass

    httpx.HTTPStatusError = HTTPStatusError
    httpx.AsyncClient = AsyncClient

    # ── App stubs ──
    _make_module("app")
    _make_module("app.core")
    _make_module("app.services")
    _make_module("app.dependencies")
    _make_module("app.models")

    # app.config with settings
    app_config = _make_module("app.config")

    class _Settings:
        TAVILY_API_KEY = ""

    app_config.settings = _Settings()

    # app.models.system_config
    app_models_system_config = _make_module("app.models.system_config")

    class SystemConfig:
        key = None
        value = None
        description = None
        updated_by = None
        updated_at = None

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    app_models_system_config.SystemConfig = SystemConfig

    app_core_database = _make_module("app.core.database")
    app_core_database.get_db = object()

    app_core_exceptions = _make_module("app.core.exceptions")

    class BizError(Exception):
        def __init__(self, code, message, status_code=400):
            super().__init__(message)
            self.code = code
            self.message = message
            self.status_code = status_code

    app_core_exceptions.BizError = BizError

    app_core_permissions = _make_module("app.core.permissions")
    app_core_permissions.require_permission = lambda _perm: object()

    app_deps = sys.modules["app.dependencies"]
    app_deps.get_current_admin = object()

    app_models_admin = _make_module("app.models.admin")

    class AdminUser:
        def __init__(self, id=None):
            self.id = id or uuid.uuid4()

    app_models_admin.AdminUser = AdminUser

    return AdminUser, BizError


# Run stubs at import time so modules can be loaded
_AdminUser, _BizError = _setup_stubs()

# Load real service modules
_config_service = _load_module(
    "app.services.web_search_config_service",
    SERVER_DIR / "app" / "services" / "web_search_config_service.py",
)
_tavily_service = _load_module(
    "app.services.tavily_service",
    SERVER_DIR / "app" / "services" / "tavily_service.py",
)
_api = _load_module(
    "admin_web_search",
    SERVER_DIR / "app" / "api" / "v1" / "admin_web_search.py",
)


class AdminWebSearchUnitTests(unittest.IsolatedAsyncioTestCase):

    async def test_get_config_returns_masked_key(self):
        """GET /config should mask the API key."""
        admin = _AdminUser()
        db = _FakeDB()

        with patch.object(
            _config_service, "get_config", new=AsyncMock(return_value=deepcopy(DEFAULT_CONFIG))
        ):
            result = await _api.get_config(admin=admin, db=db)

        self.assertEqual(result["key"], "web_search_tavily")
        api_key = result["value"]["api_key"]
        self.assertIn("****", api_key)
        self.assertNotEqual(api_key, DEFAULT_CONFIG["api_key"])

    async def test_update_config_returns_masked_key(self):
        """PUT /config should save config and return masked key."""
        admin = _AdminUser()
        db = _FakeDB()

        with patch.object(
            _config_service,
            "update_config",
            new=AsyncMock(return_value=deepcopy(DEFAULT_CONFIG)),
        ):
            body = _api.ConfigUpdateRequest(value={"max_results": 5})
            result = await _api.update_config(body=body, admin=admin, db=db)

        self.assertIn("****", result["value"]["api_key"])

    async def test_validate_key_valid(self):
        """POST /config/validate with a valid key should return valid=True."""
        admin = _AdminUser()
        db = _FakeDB()

        with patch.object(_config_service, "get_api_key", return_value="tvly-test"):
            with patch.object(_tavily_service, "validate_api_key", new=AsyncMock(return_value=True)):
                result = await _api.validate_api_key(body=None, admin=admin, db=db)

        self.assertTrue(result["valid"])
        self.assertIn("有效", result["message"])

    async def test_validate_key_invalid(self):
        """POST /config/validate with an invalid key should return valid=False."""
        admin = _AdminUser()
        db = _FakeDB()

        with patch.object(_config_service, "get_api_key", return_value="bad-key"):
            with patch.object(_tavily_service, "validate_api_key", new=AsyncMock(return_value=False)):
                result = await _api.validate_api_key(body=None, admin=admin, db=db)

        self.assertFalse(result["valid"])
        self.assertIn("无效", result["message"])

    async def test_validate_key_no_key_raises(self):
        """POST /config/validate with no key configured should raise BizError."""
        admin = _AdminUser()
        db = _FakeDB()

        with patch.object(_config_service, "get_api_key", return_value=""):
            with self.assertRaises(_BizError):
                await _api.validate_api_key(body=None, admin=admin, db=db)

    async def test_search_success(self):
        """POST /search should proxy to tavily_service.search with global config."""
        admin = _AdminUser()
        db = _FakeDB()

        tavily_response = {
            "query": "北京师范大学招生",
            "answer": "一段摘要",
            "results": [
                {"title": "招生简章", "url": "https://bnu.edu.cn", "content": "...", "score": 0.95}
            ],
            "response_time": 1.23,
        }

        with patch.object(
            _config_service, "get_config", new=AsyncMock(return_value=deepcopy(DEFAULT_CONFIG))
        ):
            with patch.object(_config_service, "get_api_key", return_value="tvly-test"):
                with patch.object(
                    _tavily_service, "search", new=AsyncMock(return_value=tavily_response)
                ):
                    body = _api.SearchRequest(query="北京师范大学招生")
                    result = await _api.search(body=body, admin=admin, db=db)

        self.assertEqual(result["query"], "北京师范大学招生")
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["title"], "招生简章")

    async def test_search_no_api_key_raises(self):
        """POST /search without configured API key should raise BizError."""
        admin = _AdminUser()
        db = _FakeDB()

        with patch.object(
            _config_service, "get_config", new=AsyncMock(return_value={**DEFAULT_CONFIG, "api_key": ""})
        ):
            with patch.object(_config_service, "get_api_key", return_value=""):
                with self.assertRaises(_BizError):
                    body = _api.SearchRequest(query="test")
                    await _api.search(body=body, admin=admin, db=db)

    async def test_search_disabled_raises(self):
        """POST /search when search is disabled should raise BizError."""
        admin = _AdminUser()
        db = _FakeDB()

        disabled_config = {**DEFAULT_CONFIG, "enabled": False}
        with patch.object(
            _config_service, "get_config", new=AsyncMock(return_value=disabled_config)
        ):
            with self.assertRaises(_BizError) as ctx:
                body = _api.SearchRequest(query="test")
                await _api.search(body=body, admin=admin, db=db)
            self.assertIn("已关闭", ctx.exception.message)

    async def test_search_passes_all_config_params(self):
        """POST /search should pass all global config params to tavily."""
        admin = _AdminUser()
        db = _FakeDB()

        full_config = {
            **DEFAULT_CONFIG,
            "search_depth": "advanced",
            "max_results": 5,
            "include_domains": ["bnu.edu.cn", "example.com"],
            "exclude_domains": ["spam.com"],
            "include_answer": "advanced",
            "include_raw_content": "markdown",
            "topic": "news",
            "country": "cn",
            "time_range": "week",
            "chunks_per_source": 2,
            "include_images": True,
        }

        captured = {}

        async def fake_search(**kwargs):
            captured.update(kwargs)
            return {"query": kwargs["query"], "results": [], "response_time": 0.5}

        with patch.object(
            _config_service, "get_config", new=AsyncMock(return_value=full_config)
        ):
            with patch.object(_config_service, "get_api_key", return_value="tvly-test"):
                with patch.object(_tavily_service, "search", side_effect=fake_search):
                    body = _api.SearchRequest(query="test")
                    await _api.search(body=body, admin=admin, db=db)

        self.assertEqual(captured["search_depth"], "advanced")
        self.assertEqual(captured["max_results"], 5)
        self.assertEqual(captured["include_domains"], ["bnu.edu.cn", "example.com"])
        self.assertEqual(captured["exclude_domains"], ["spam.com"])
        self.assertEqual(captured["include_answer"], "advanced")
        self.assertEqual(captured["include_raw_content"], "markdown")
        self.assertEqual(captured["topic"], "news")
        self.assertEqual(captured["country"], "cn")
        self.assertEqual(captured["time_range"], "week")
        self.assertEqual(captured["chunks_per_source"], 2)
        self.assertTrue(captured["include_images"])


class ConfigServiceUnitTests(unittest.TestCase):
    """Tests for web_search_config_service helper functions."""

    def test_mask_key_short(self):
        self.assertEqual(_config_service._mask_key("abc"), "****")

    def test_mask_key_long(self):
        result = _config_service._mask_key("tvly-abcdef123456")
        self.assertEqual(result, "tvly****3456")
        self.assertNotIn("abcdef", result)

    def test_mask_key_empty(self):
        self.assertEqual(_config_service._mask_key(""), "")

    def test_normalize_defaults(self):
        result = _config_service._normalize(None)
        self.assertEqual(result["search_depth"], "basic")
        self.assertEqual(result["max_results"], 10)
        self.assertEqual(result["topic"], "general")
        self.assertTrue(result["enabled"])
        self.assertEqual(result["country"], "")
        self.assertEqual(result["time_range"], "")
        self.assertEqual(result["chunks_per_source"], 3)
        self.assertFalse(result["include_images"])

    def test_normalize_clamps_max_results(self):
        result = _config_service._normalize({"max_results": 100})
        self.assertEqual(result["max_results"], 20)

        result = _config_service._normalize({"max_results": -5})
        self.assertEqual(result["max_results"], 1)

    def test_normalize_search_depth_all_values(self):
        for depth in ("ultra-fast", "fast", "basic", "advanced"):
            result = _config_service._normalize({"search_depth": depth})
            self.assertEqual(result["search_depth"], depth)

        result = _config_service._normalize({"search_depth": "invalid"})
        self.assertEqual(result["search_depth"], "basic")

    def test_normalize_topic_finance(self):
        result = _config_service._normalize({"topic": "finance"})
        self.assertEqual(result["topic"], "finance")

    def test_normalize_include_answer_modes(self):
        for val in (False, True, "basic", "advanced"):
            result = _config_service._normalize({"include_answer": val})
            self.assertEqual(result["include_answer"], val)

    def test_normalize_include_raw_content_modes(self):
        for val in (False, True, "markdown", "text"):
            result = _config_service._normalize({"include_raw_content": val})
            self.assertEqual(result["include_raw_content"], val)

    def test_normalize_country(self):
        result = _config_service._normalize({"country": "CN"})
        self.assertEqual(result["country"], "cn")

    def test_normalize_time_range(self):
        for tr in ("day", "week", "month", "year"):
            result = _config_service._normalize({"time_range": tr})
            self.assertEqual(result["time_range"], tr)

        result = _config_service._normalize({"time_range": "invalid"})
        self.assertEqual(result["time_range"], "")

    def test_normalize_enabled_flag(self):
        result = _config_service._normalize({"enabled": False})
        self.assertFalse(result["enabled"])

        result = _config_service._normalize({"enabled": True})
        self.assertTrue(result["enabled"])

    def test_normalize_preserves_masked_key(self):
        result = _config_service._normalize(
            {"api_key": "tvly****3456"}, existing_key="tvly-abcdef123456"
        )
        self.assertEqual(result["api_key"], "tvly-abcdef123456")

    def test_normalize_domains_lowercased(self):
        result = _config_service._normalize({"include_domains": ["BNU.EDU.CN", " Example.COM "]})
        self.assertEqual(result["include_domains"], ["bnu.edu.cn", "example.com"])

    def test_normalize_chunks_per_source_clamped(self):
        result = _config_service._normalize({"chunks_per_source": 10})
        self.assertEqual(result["chunks_per_source"], 3)

        result = _config_service._normalize({"chunks_per_source": 0})
        self.assertEqual(result["chunks_per_source"], 1)

    def test_is_enabled(self):
        _config_service._refresh({"enabled": True, "api_key": ""})
        self.assertTrue(_config_service.is_enabled())

        _config_service._refresh({"enabled": False, "api_key": ""})
        self.assertFalse(_config_service.is_enabled())

        # Reset
        _config_service._refresh(None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
