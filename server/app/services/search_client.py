"""HTTP client for the search microservice."""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        headers = {}
        if settings.SEARCH_SERVICE_API_KEY:
            headers["Authorization"] = f"Bearer {settings.SEARCH_SERVICE_API_KEY}"
        _client = httpx.AsyncClient(
            base_url=settings.SEARCH_SERVICE_URL,
            timeout=30.0,
            headers=headers,
        )
    return _client


async def health_check() -> dict:
    resp = await _get_client().get("/health")
    resp.raise_for_status()
    return resp.json()


async def create_site(data: dict) -> dict:
    resp = await _get_client().post("/sites", json=data)
    resp.raise_for_status()
    return resp.json()


async def update_site(site_id: str, data: dict) -> dict:
    resp = await _get_client().put(f"/sites/{site_id}", json=data)
    resp.raise_for_status()
    return resp.json()


async def delete_site(site_id: str) -> dict:
    resp = await _get_client().delete(f"/sites/{site_id}")
    resp.raise_for_status()
    return resp.json()


async def trigger_crawl(site_id: str) -> dict:
    resp = await _get_client().post(f"/sites/{site_id}/crawl")
    resp.raise_for_status()
    return resp.json()


async def get_crawl_task(task_id: str) -> dict:
    resp = await _get_client().get(f"/crawl/{task_id}")
    resp.raise_for_status()
    return resp.json()


async def list_crawl_tasks(page: int = 1, page_size: int = 20) -> dict:
    resp = await _get_client().get(
        "/crawl/tasks", params={"page": page, "page_size": page_size}
    )
    resp.raise_for_status()
    return resp.json()


async def search(
    query: str,
    domain: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    resp = await _get_client().post(
        "/search",
        json={"query": query, "domain": domain, "page": page, "page_size": page_size},
    )
    resp.raise_for_status()
    return resp.json()
