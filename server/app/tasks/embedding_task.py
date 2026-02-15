"""Celery task: embedding generation for knowledge chunks."""

import logging
from app.tasks.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.embedding_task.generate_embeddings")
def generate_embeddings_task(document_id: str, chunks: list[str]):
    """Generate embeddings for document chunks and store in DB."""
    logger.info("Generating embeddings for document %s (%d chunks)", document_id, len(chunks))

    # Note: In production this would:
    # 1. Call embedding_service.generate_embeddings(chunks) in batches
    # 2. Write KnowledgeChunk records with embeddings to DB
    # 3. Update KnowledgeDocument status to 'approved'
    # For now, this is a placeholder that will be fully implemented
    # when the LLM provider is configured.

    return {"document_id": document_id, "chunks_processed": len(chunks), "status": "embedded"}
