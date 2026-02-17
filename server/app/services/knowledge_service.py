"""Knowledge base vector search service using pgvector."""

import logging
import re
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
    vector_score: float = 0.0
    lexical_score: float = 0.0


_EN_TOKEN_RE = re.compile(r"[a-z0-9_]{2,}")
_ZH_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]")


def _tokenize(text: str) -> set[str]:
    text_lower = text.lower()
    tokens = set(_EN_TOKEN_RE.findall(text_lower))
    tokens.update(_ZH_TOKEN_RE.findall(text_lower))
    return tokens


def _lexical_score(query: str, content: str) -> float:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return 0.0
    content_tokens = _tokenize(content)
    if not content_tokens:
        return 0.0

    overlap = len(query_tokens & content_tokens)
    coverage = overlap / max(1, len(query_tokens))
    query_lower = query.lower().strip()
    phrase_bonus = 0.15 if query_lower and query_lower in content.lower() else 0.0
    return min(1.0, coverage + phrase_bonus)


def _hybrid_rerank(results: list[SearchResult], query: str) -> list[SearchResult]:
    for r in results:
        lexical = _lexical_score(query, r.content)
        r.lexical_score = lexical
        # 二次精排：向量分为主，词法匹配为辅
        r.score = r.vector_score * 0.75 + lexical * 0.25

    # 排序：综合分 -> 向量分 -> chunk_id（稳定）
    return sorted(results, key=lambda r: (r.score, r.vector_score, r.chunk_id), reverse=True)


async def search(
    query: str,
    db: AsyncSession,
    top_k: int = 5,
    recall_k: int | None = None,
    min_vector_score: float = 0.15,
    min_hybrid_score: float = 0.20,
) -> list[SearchResult]:
    """Search knowledge base using vector similarity.

    Two-stage pipeline:
    1) 向量召回（recall_k）
    2) 二次精排（向量分 + 词法分混合）
    3) 按阈值过滤并返回 top_k
    """
    if recall_k is None:
        recall_k = max(20, top_k * 6)

    try:
        embeddings = await generate_embeddings([query])
        query_vector = embeddings[0]
    except Exception as e:
        logger.warning("Embedding generation failed, falling back to empty results: %s", e)
        return []

    # embedding 退化保护：全零向量时直接返回空结果，避免无效召回
    if not query_vector or max(abs(v) for v in query_vector) < 1e-9:
        logger.warning("Embedding result is near-zero vector, skip retrieval")
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
                LIMIT :recall_k
    """)

    try:
        # Use a savepoint so failures don't taint the outer transaction
        async with db.begin_nested():
            result = await db.execute(stmt, {"query_vec": vector_str, "recall_k": recall_k})
            rows = result.fetchall()

        recalled = [
            SearchResult(
                chunk_id=str(row[0]),
                document_id=str(row[1]),
                document_title=row[2],
                content=row[3],
                score=float(row[4]),
                vector_score=float(row[4]),
            )
            for row in rows
            if float(row[4]) >= min_vector_score
        ]

        reranked = _hybrid_rerank(recalled, query)
        filtered = [r for r in reranked if r.score >= min_hybrid_score]
        return filtered[:top_k]
    except Exception as e:
        logger.error("Knowledge search failed: %s", e)
        return []


def format_sources_for_prompt(results: list[SearchResult]) -> str:
    """Format search results as context for LLM prompt."""
    if not results:
        return ""
    parts = []
    for i, r in enumerate(results, 1):
        parts.append(
            f"[来源{i}] 文档：{r.document_title}\n"
            f"相关度：{r.score:.3f}\n"
            f"内容：{r.content}"
        )
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
