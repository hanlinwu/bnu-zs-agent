import datetime as dt
import importlib.util
import sys
import types
import unittest
import uuid
from pathlib import Path

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


class _Field:
    def desc(self):
        return self

    def __eq__(self, _other):
        return self


class _Select:
    def __init__(self, _model):
        self.model = _model

    def order_by(self, *_args, **_kwargs):
        return self

    def where(self, *_args, **_kwargs):
        return self


class _ExecuteResult:
    def __init__(self, scalar=None, scalars_list=None):
        self._scalar = scalar
        self._scalars_list = scalars_list or []

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        return self

    def all(self):
        return self._scalars_list


class _FakeDB:
    def __init__(self, execute_results=None):
        self.execute_results = list(execute_results or [])
        self.added = []
        self.deleted = []
        self.commits = 0

    async def execute(self, _query):
        if self.execute_results:
            return self.execute_results.pop(0)
        return _ExecuteResult()

    def add(self, obj):
        now = dt.datetime.now(dt.timezone.utc)
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if getattr(obj, "created_at", None) is None:
            obj.created_at = now
        if getattr(obj, "updated_at", None) is None:
            obj.updated_at = now
        self.added.append(obj)

    async def delete(self, obj):
        self.deleted.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        if getattr(obj, "updated_at", None) is None:
            obj.updated_at = dt.datetime.now(dt.timezone.utc)


class AdminWebSearchUnitTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        # minimal stubs for external dependencies
        fastapi = _make_module("fastapi")

        class APIRouter:
            def get(self, *_args, **_kwargs):
                return lambda fn: fn

            def post(self, *_args, **_kwargs):
                return lambda fn: fn

            def put(self, *_args, **_kwargs):
                return lambda fn: fn

            def delete(self, *_args, **_kwargs):
                return lambda fn: fn

        fastapi.APIRouter = APIRouter
        fastapi.Depends = lambda x: x
        fastapi.Query = lambda default=None, **_kwargs: default

        pydantic = _make_module("pydantic")

        class BaseModel:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        pydantic.BaseModel = BaseModel

        sqlalchemy = _make_module("sqlalchemy")
        sqlalchemy.select = lambda model: _Select(model)

        sqlalchemy_ext = _make_module("sqlalchemy.ext")
        sqlalchemy_ext_asyncio = _make_module("sqlalchemy.ext.asyncio")
        sqlalchemy_ext.asyncio = sqlalchemy_ext_asyncio

        class AsyncSession:
            pass

        sqlalchemy_ext_asyncio.AsyncSession = AsyncSession

        app = _make_module("app")
        app_core = _make_module("app.core")
        app_services = _make_module("app.services")
        _make_module("app.dependencies")
        _make_module("app.models")

        app_core_database = _make_module("app.core.database")
        app_core_database.get_db = object()

        app_core_exceptions = _make_module("app.core.exceptions")

        class NotFoundError(Exception):
            pass

        class BizError(Exception):
            def __init__(self, code, message, status_code=400):
                super().__init__(message)
                self.code = code
                self.message = message
                self.status_code = status_code

        app_core_exceptions.NotFoundError = NotFoundError
        app_core_exceptions.BizError = BizError

        app_core_permissions = _make_module("app.core.permissions")
        app_core_permissions.require_permission = lambda _perm: object()

        app_dependencies = sys.modules["app.dependencies"]
        app_dependencies.get_current_admin = object()

        app_models_admin = _make_module("app.models.admin")

        class AdminUser:
            def __init__(self, id):
                self.id = id

        app_models_admin.AdminUser = AdminUser

        app_models_web_search = _make_module("app.models.web_search")

        class WebSearchSite:
            id = _Field()
            created_at = _Field()

            def __init__(
                self,
                domain,
                name,
                start_url,
                max_depth=3,
                max_pages=100,
                same_domain_only=True,
                crawl_frequency_minutes=1440,
                enabled=True,
                created_by=None,
            ):
                self.id = None
                self.domain = domain
                self.name = name
                self.start_url = start_url
                self.max_depth = max_depth
                self.max_pages = max_pages
                self.same_domain_only = same_domain_only
                self.crawl_frequency_minutes = crawl_frequency_minutes
                self.enabled = enabled
                self.remote_site_id = None
                self.last_crawl_at = None
                self.last_crawl_status = None
                self.created_by = created_by
                self.created_at = None
                self.updated_at = None

        app_models_web_search.WebSearchSite = WebSearchSite

        search_client = types.SimpleNamespace(
            create_site=None,
            update_site=None,
            delete_site=None,
            trigger_crawl=None,
            list_crawl_tasks=None,
            get_crawl_task=None,
            search=None,
            health_check=None,
        )
        app_services.search_client = search_client

        cls.admin_web_search = _load_module(
            "admin_web_search",
            SERVER_DIR / "app" / "api" / "v1" / "admin_web_search.py",
        )

    async def test_create_site_syncs_remote_id(self):
        m = self.admin_web_search
        admin = m.AdminUser(id=uuid.uuid4())
        db = _FakeDB()

        async def fake_create_site(_payload):
            return {"id": "remote-123"}

        m.search_client.create_site = fake_create_site

        body = m.SiteCreateRequest(
            domain="example.com",
            name="Example",
            start_url="https://example.com",
            max_depth=2,
            max_pages=50,
            same_domain_only=True,
            crawl_frequency_minutes=60,
            enabled=True,
        )
        result = await m.create_site(body=body, admin=admin, db=db)

        self.assertEqual(result["domain"], "example.com")
        self.assertEqual(result["remote_site_id"], "remote-123")
        self.assertGreaterEqual(db.commits, 2)

    async def test_trigger_site_crawl_syncs_then_triggers(self):
        m = self.admin_web_search
        admin = m.AdminUser(id=uuid.uuid4())

        site = m.WebSearchSite(
            domain="example.com",
            name="Example",
            start_url="https://example.com",
            created_by=admin.id,
        )
        site.id = uuid.uuid4()
        site.created_at = dt.datetime.now(dt.timezone.utc)
        site.updated_at = dt.datetime.now(dt.timezone.utc)

        db = _FakeDB(execute_results=[_ExecuteResult(scalar=site)])

        async def fake_create_site(_payload):
            return {"id": "remote-site-1"}

        async def fake_trigger_crawl(remote_id):
            self.assertEqual(remote_id, "remote-site-1")
            return {"task_id": "task-1", "status": "pending"}

        m.search_client.create_site = fake_create_site
        m.search_client.trigger_crawl = fake_trigger_crawl

        result = await m.trigger_site_crawl(site_id=str(site.id), admin=admin, db=db)

        self.assertEqual(result["task_id"], "task-1")
        self.assertEqual(site.remote_site_id, "remote-site-1")
        self.assertEqual(site.last_crawl_status, "running")

    async def test_search_query_proxies_result(self):
        m = self.admin_web_search
        admin = m.AdminUser(id=uuid.uuid4())

        async def fake_search(query, domain=None, page=1, page_size=20):
            return {
                "query": query,
                "domain": domain,
                "page": page,
                "page_size": page_size,
                "total": 1,
                "hits": [{"id": "doc-1", "title": "招生简章"}],
            }

        m.search_client.search = fake_search
        body = m.SearchQueryRequest(query="招生", domain="example.com", page=1, page_size=10)

        result = await m.search_query(body=body, admin=admin)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["hits"][0]["title"], "招生简章")


if __name__ == "__main__":
    unittest.main(verbosity=2)
