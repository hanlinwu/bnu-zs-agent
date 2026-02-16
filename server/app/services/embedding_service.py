"""Embedding service — uses DB-configured embedding model or falls back gracefully."""

import logging

import httpx

logger = logging.getLogger(__name__)

_client = httpx.AsyncClient(timeout=30.0)


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts.

    Reads config from model_config_service (DB-driven).
    Falls back to env vars if DB config not available.
    Returns zero vectors on failure so chat is never blocked by embedding issues.
    """
    from app.services.model_config_service import get_embedding_config

    config = get_embedding_config()
    if config:
        base_url = config["base_url"].rstrip("/")
        api_key = config["api_key"]
        model = config["model"]
    else:
        # Fallback to env vars for backward compatibility
        from app.config import settings
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
