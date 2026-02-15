"""Embedding service — wraps LLM provider's embed() method."""

from app.services.llm_service import llm_router


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using the configured LLM provider."""
    return await llm_router.embed(texts)
