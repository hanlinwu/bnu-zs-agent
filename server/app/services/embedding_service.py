"""Embedding service — uses DB-configured embedding model or falls back gracefully."""

import logging

import httpx

logger = logging.getLogger(__name__)

_client = httpx.AsyncClient(timeout=30.0)


async def generate_embeddings_with_model(texts: list[str]) -> tuple[list[list[float]], str]:
    """Generate embeddings using the embedding model from system configuration.

    Returns: (embeddings, model_name)
    """
    from app.services.model_config_service import get_embedding_config

    config = get_embedding_config()
    if not config:
        raise RuntimeError("Embedding model is not configured in system model settings")

    base_url = config["base_url"].rstrip("/")
    api_key = config["api_key"]
    model = config["model"]

    if not base_url or not api_key:
        raise RuntimeError("Embedding provider base_url/api_key is missing in system model settings")

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
    return [item["embedding"] for item in data["data"]], model


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    embeddings, _ = await generate_embeddings_with_model(texts)
    return embeddings
