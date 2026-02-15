"""Embedding service — uses a dedicated embedding model or falls back gracefully."""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_client = httpx.AsyncClient(timeout=30.0)


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts.

    Uses EMBEDDING_* config if set, otherwise falls back to the primary LLM provider.
    Returns zero vectors on failure so chat is never blocked by embedding issues.
    """
    base_url = (settings.EMBEDDING_BASE_URL or settings.LLM_PRIMARY_BASE_URL).rstrip("/")
    api_key = settings.EMBEDDING_API_KEY or settings.LLM_PRIMARY_API_KEY
    model = settings.EMBEDDING_MODEL

    if not base_url or not api_key:
        logger.warning("No embedding provider configured, returning empty results")
        return [[0.0] * 1536 for _ in texts]

    try:
        resp = await _client.post(
            f"{base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": model, "input": texts},
        )
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]
    except Exception as e:
        logger.warning("Embedding generation failed, returning empty results: %s", e)
        return [[0.0] * 1536 for _ in texts]
