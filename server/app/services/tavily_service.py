"""Tavily web search API client."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TAVILY_API_URL = "https://api.tavily.com/search"

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=30.0)
    return _client


async def search(
    api_key: str,
    query: str,
    search_depth: str = "basic",
    max_results: int = 10,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    include_answer: bool | str = False,
    include_raw_content: bool | str = False,
    topic: str = "general",
    country: str = "",
    time_range: str = "",
    chunks_per_source: int = 3,
    include_images: bool = False,
) -> dict[str, Any]:
    """Call Tavily Search API.

    Returns dict with keys: query, answer, results, response_time, images, etc.
    Each result has: title, url, content, score, raw_content (optional).
    """
    payload: dict[str, Any] = {
        "api_key": api_key,
        "query": query,
        "search_depth": search_depth,
        "max_results": max_results,
        "topic": topic,
    }
    # Only include optional params when they have meaningful values
    if include_answer:
        payload["include_answer"] = include_answer
    if include_raw_content:
        payload["include_raw_content"] = include_raw_content
    if include_domains:
        payload["include_domains"] = include_domains
    if exclude_domains:
        payload["exclude_domains"] = exclude_domains
    if country and topic == "general" and search_depth in ("basic", "advanced"):
        payload["country"] = country
    if time_range:
        payload["time_range"] = time_range
    if search_depth == "advanced" and chunks_per_source != 3:
        payload["chunks_per_source"] = chunks_per_source
    if include_images:
        payload["include_images"] = True

    logger.debug("Tavily request payload: %s", {k: v for k, v in payload.items() if k != "api_key"})
    resp = await _get_client().post(TAVILY_API_URL, json=payload)
    if resp.status_code != 200:
        logger.error("Tavily API error %s: %s", resp.status_code, resp.text)
    resp.raise_for_status()
    return resp.json()


async def validate_api_key(api_key: str) -> bool:
    """Validate a Tavily API key by making a minimal search."""
    try:
        await search(api_key=api_key, query="test", max_results=1)
        return True
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (401, 403):
            return False
        raise
