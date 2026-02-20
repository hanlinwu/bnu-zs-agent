"""Embedding service — uses DB-configured embedding model or falls back gracefully."""

import logging

import httpx

logger = logging.getLogger(__name__)

_client = httpx.AsyncClient(timeout=30.0)


async def generate_embeddings_with_model(texts: list[str]) -> tuple[list[list[float]], str]:
    """Generate embeddings using the embedding model from system configuration.

    Returns: (embeddings, model_name)
    """
    from app.services.model_config_service import pick_embedding_provider_sequence

    last_error: Exception | None = None
    for provider in pick_embedding_provider_sequence():
        base_url = str(provider.get("base_url", "")).rstrip("/")
        api_key = provider.get("api_key")
        model = provider.get("model")
        if not base_url or not api_key or not model:
            continue
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
            return [item["embedding"] for item in data["data"]], str(model)
        except Exception as error:
            logger.warning("Embedding provider %s failed: %s", provider.get("name") or model, error)
            last_error = error
            continue

    raise RuntimeError(f"All embedding providers failed. Last error: {last_error}")


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    embeddings, _ = await generate_embeddings_with_model(texts)
    return embeddings
