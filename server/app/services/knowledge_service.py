"""Knowledge base vector search service using pgvector."""

import logging
from dataclasses import dataclass

from sqlalchemy import text as sa_text, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeDocument, KnowledgeChunk
from app.services.embedding_service import generate_embeddings

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    document_title: str
    content: str
    score: float


async def search(query: str, db: AsyncSession, top_k: int = 5) -> list[SearchResult]:
    """Search knowledge base using vector similarity.

    1. Embed the query
    2. Use pgvector cosine similarity to find top-k chunks
    3. Return with document metadata
    """
    try:
        embeddings = await generate_embeddings([query])
        query_vector = embeddings[0]
    except Exception as e:
        logger.warning("Embedding generation failed, falling back to empty results: %s", e)
        return []

    # pgvector cosine distance query
    vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"
    stmt = sa_text("""
        SELECT
            kc.id as chunk_id,
            kc.document_id,
            kd.title as document_title,
            kc.content,
            1 - (kc.embedding <=> CAST(:query_vec AS vector)) as score
        FROM knowledge_chunks kc
        JOIN knowledge_documents kd ON kd.id = kc.document_id
        JOIN knowledge_bases kb ON kb.id = kd.kb_id
        WHERE kd.status = 'approved'
          AND kb.enabled = true
          AND kc.embedding IS NOT NULL
        ORDER BY kc.embedding <=> CAST(:query_vec AS vector)
        LIMIT :top_k
    """)

    try:
        # Use a savepoint so failures don't taint the outer transaction
        async with db.begin_nested():
            result = await db.execute(stmt, {"query_vec": vector_str, "top_k": top_k})
            rows = result.fetchall()
        return [
            SearchResult(
                chunk_id=str(row[0]),
                document_id=str(row[1]),
                document_title=row[2],
                content=row[3],
                score=float(row[4]),
            )
            for row in rows
        ]
    except Exception as e:
        logger.error("Knowledge search failed: %s", e)
        return []


def format_sources_for_prompt(results: list[SearchResult]) -> str:
    """Format search results as context for LLM prompt."""
    if not results:
        return ""
    parts = []
    for i, r in enumerate(results, 1):
        parts.append(f"[来源{i}] {r.document_title}:\n{r.content}")
    return "\n\n".join(parts)


def format_sources_for_citation(results: list[SearchResult]) -> list[dict]:
    """Format search results for citation display in frontend."""
    return [
        {
            "doc_id": r.document_id,
            "title": r.document_title,
            "chunk": r.content[:200],
            "score": round(r.score, 3),
        }
        for r in results
    ]
