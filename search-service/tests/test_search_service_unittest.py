import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path

SEARCH_DIR = Path(__file__).resolve().parents[1]


def _load_module(name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(name, str(file_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class SearchServiceUnitTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        # Stub dependencies missing in the current runtime.
        if "pydantic_settings" not in sys.modules:
            pydantic_settings = types.ModuleType("pydantic_settings")

            class BaseSettings:
                pass

            class SettingsConfigDict(dict):
                def __init__(self, **kwargs):
                    super().__init__(**kwargs)

            pydantic_settings.BaseSettings = BaseSettings
            pydantic_settings.SettingsConfigDict = SettingsConfigDict
            sys.modules["pydantic_settings"] = pydantic_settings

        if "meilisearch_python_sdk" not in sys.modules:
            meili = types.ModuleType("meilisearch_python_sdk")

            class AsyncClient:
                def __init__(self, *_args, **_kwargs):
                    pass

            meili.AsyncClient = AsyncClient
            sys.modules["meilisearch_python_sdk"] = meili

        if "aiosqlite" not in sys.modules:
            aiosqlite = types.ModuleType("aiosqlite")

            class Connection:
                pass

            class Row(dict):
                pass

            async def connect(*_args, **_kwargs):  # pragma: no cover
                raise RuntimeError("connect() should not be called in this unit test")

            aiosqlite.Connection = Connection
            aiosqlite.Row = Row
            aiosqlite.connect = connect
            sys.modules["aiosqlite"] = aiosqlite

        if "crawl4ai" not in sys.modules:
            crawl4ai = types.ModuleType("crawl4ai")

            class BrowserConfig:
                def __init__(self, **kwargs):
                    self.kwargs = kwargs

            class CrawlerRunConfig:
                def __init__(self, **kwargs):
                    self.kwargs = kwargs

            class AsyncWebCrawler:
                def __init__(self, *_args, **_kwargs):
                    pass

                async def __aenter__(self):
                    return self

                async def __aexit__(self, exc_type, exc, tb):
                    return False

                async def arun(self, *_args, **_kwargs):  # pragma: no cover
                    raise RuntimeError("arun() should be monkeypatched in tests")

            crawl4ai.BrowserConfig = BrowserConfig
            crawl4ai.CrawlerRunConfig = CrawlerRunConfig
            crawl4ai.AsyncWebCrawler = AsyncWebCrawler
            sys.modules["crawl4ai"] = crawl4ai

        _load_module("config", SEARCH_DIR / "config.py")
        _load_module("database", SEARCH_DIR / "database.py")
        cls.search_service = _load_module("search_service", SEARCH_DIR / "search_service.py")
        cls.crawl_service = _load_module("crawl_service", SEARCH_DIR / "crawl_service.py")

    async def test_search_maps_meili_hits(self):
        class FakeResult:
            def __init__(self):
                self.hits = [
                    {
                        "id": "doc-1",
                        "url": "https://example.com/a",
                        "title": "A",
                        "content": "raw-content",
                        "domain": "example.com",
                        "crawled_at": "2026-02-21T00:00:00+00:00",
                        "_formatted": {"content": "formatted-content"},
                        "_rankingScore": 0.88,
                    }
                ]
                self.estimated_total_hits = 1

        class FakeIndex:
            async def search(self, query, **kwargs):
                self.query = query
                self.kwargs = kwargs
                return FakeResult()

        class FakeClient:
            def __init__(self):
                self.idx = FakeIndex()

            def index(self, _name):
                return self.idx

        svc = self.search_service.MeiliSearchService()
        svc._client = FakeClient()
        result = await svc.search("招生", domain="example.com", page=2, page_size=5)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["query"], "招生")
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["hits"][0]["content_snippet"], "formatted-content")

    async def test_run_crawl_indexes_pages_and_finishes_success(self):
        docs_indexed = []
        task_updates = []

        class FakeDB:
            async def close(self):
                return None

        class FakeResult:
            def __init__(self, success, markdown, title, links):
                self.success = success
                self.markdown = markdown
                self.metadata = {"title": title}
                self.links = links

        class FakeCrawler:
            def __init__(self, *_args, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def arun(self, url, config=None):
                if url.endswith("/start"):
                    return FakeResult(
                        True,
                        "start page content",
                        "Start",
                        {"internal": [{"href": "/about"}]},
                    )
                if url.endswith("/about"):
                    return FakeResult(True, "about page content", "About", {"internal": []})
                return FakeResult(False, "", "", {"internal": []})

        async def fake_get_db():
            return FakeDB()

        async def fake_update_task(_db, _task_id, **fields):
            task_updates.append(fields)

        async def fake_index_pages(batch):
            docs_indexed.extend(batch)

        old_get_db = self.crawl_service.get_db
        old_update_task = self.crawl_service._update_task
        old_index_pages = self.crawl_service.meili_service.index_pages
        old_delay = self.crawl_service.settings.CRAWL_DELAY_MS
        old_crawler = self.crawl_service.AsyncWebCrawler

        self.crawl_service.get_db = fake_get_db
        self.crawl_service._update_task = fake_update_task
        self.crawl_service.meili_service.index_pages = fake_index_pages
        self.crawl_service.settings.CRAWL_DELAY_MS = 0
        self.crawl_service.AsyncWebCrawler = FakeCrawler

        try:
            await self.crawl_service.run_crawl(
                task_id="task-1",
                start_url="https://example.com/start",
                max_depth=2,
                max_pages=10,
                same_domain_only=True,
                domain_restriction="example.com",
            )
        finally:
            self.crawl_service.get_db = old_get_db
            self.crawl_service._update_task = old_update_task
            self.crawl_service.meili_service.index_pages = old_index_pages
            self.crawl_service.settings.CRAWL_DELAY_MS = old_delay
            self.crawl_service.AsyncWebCrawler = old_crawler

        self.assertEqual(len(docs_indexed), 2)
        self.assertTrue(any(update.get("status") == "success" for update in task_updates))
        urls = sorted(doc["url"] for doc in docs_indexed)
        self.assertEqual(urls, ["https://example.com/about", "https://example.com/start"])

    def test_url_to_doc_id_is_stable(self):
        fn = self.search_service.url_to_doc_id
        self.assertEqual(fn(" https://example.com/a "), fn("https://example.com/a"))
        self.assertNotEqual(fn("https://example.com/a"), fn("https://example.com/b"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
