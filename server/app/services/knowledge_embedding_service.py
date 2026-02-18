"""Knowledge chunk embedding maintenance service."""

from __future__ import annotations

import logging

from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeChunk
from app.services.embedding_service import generate_embeddings_with_model

logger = logging.getLogger(__name__)


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(str(v) for v in values) + "]"


async def ensure_embedding_schema(db: AsyncSession) -> None:
    """Ensure pgvector extension, embedding column, and vector index exist.

    This is strict: pgvector must be available.
    """
    await db.execute(sa_text("CREATE EXTENSION IF NOT EXISTS vector"))
    await db.execute(
        sa_text("ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS embedding vector(1536)")
    )
    await db.execute(
        sa_text("ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(120)")
    )
    await db.execute(
        sa_text(
            """
            CREATE INDEX IF NOT EXISTS idx_chunk_embedding
            ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops)
            """
        )
    )


async def embed_document_chunks(document_id: str, db: AsyncSession, batch_size: int = 32) -> int:
    """Generate and persist embeddings for all chunks of a document.

    Returns number of updated chunks.
    """
    result = await db.execute(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.document_id == document_id)
        .order_by(KnowledgeChunk.chunk_index.asc(), KnowledgeChunk.id.asc())
    )
    chunks = result.scalars().all()
    if not chunks:
        return 0

    updated = 0
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        texts = [chunk.content for chunk in batch]
        vectors, model_name = await generate_embeddings_with_model(texts)

        for chunk, vector in zip(batch, vectors):
            if not vector or max(abs(v) for v in vector) < 1e-9:
                continue

            await db.execute(
                sa_text(
                    "UPDATE knowledge_chunks "
                    "SET embedding = CAST(:embedding AS vector) "
                    "WHERE id = :chunk_id"
                ),
                {
                    "embedding": _vector_literal(vector),
                    "chunk_id": str(chunk.id),
                },
            )
            chunk.embedding_model = model_name
            updated += 1

    return updated


async def backfill_missing_embeddings(db: AsyncSession, limit: int = 500, document_id: str | None = None) -> int:
    """Backfill embeddings for chunks missing vectors, up to `limit` rows."""
    if document_id:
        query = sa_text(
            """
            SELECT id, content
            FROM knowledge_chunks
            WHERE embedding IS NULL
              AND document_id = CAST(:document_id AS uuid)
            ORDER BY created_at ASC
            LIMIT :limit
            """
        )
        rows = (await db.execute(query, {"limit": limit, "document_id": document_id})).all()
    else:
        query = sa_text(
            """
            SELECT id, content
            FROM knowledge_chunks
            WHERE embedding IS NULL
            ORDER BY created_at ASC
            LIMIT :limit
            """
        )
        rows = (await db.execute(query, {"limit": limit})).all()
    if not rows:
        return 0

    updated = 0
    batch_size = 32
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        texts = [row[1] for row in batch]
        vectors, model_name = await generate_embeddings_with_model(texts)

        for row, vector in zip(batch, vectors):
            if not vector or max(abs(v) for v in vector) < 1e-9:
                continue

            await db.execute(
                sa_text(
                    "UPDATE knowledge_chunks "
                    "SET embedding = CAST(:embedding AS vector) "
                    "WHERE id = :chunk_id"
                ),
                {
                    "embedding": _vector_literal(vector),
                    "chunk_id": str(row[0]),
                },
            )
            await db.execute(
                sa_text("UPDATE knowledge_chunks SET embedding_model = :model WHERE id = :chunk_id"),
                {
                    "model": model_name,
                    "chunk_id": str(row[0]),
                },
            )
            updated += 1

    if updated:
        logger.info("Backfilled %d chunk embeddings", updated)
    return updated
