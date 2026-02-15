"""Sensitive word filtering service with Redis caching."""

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_client
from app.models.sensitive_word import SensitiveWord, SensitiveWordGroup

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    action: str  # "pass" | "warn" | "block"
    matched_words: list[str]
    message: str | None = None


async def load_sensitive_words(db: AsyncSession | None = None) -> dict[str, str]:
    """Load all active sensitive words into Redis cache.
    Returns dict of word -> level.
    """
    cache_key = "sensitive_words:all"

    # Try cache first
    try:
        cached = await redis_client.hgetall(cache_key)
        if cached:
            return cached
    except Exception:
        pass

    if not db:
        return {}

    # Load from DB
    stmt = (
        select(SensitiveWord.word, SensitiveWord.level)
        .join(SensitiveWordGroup, SensitiveWordGroup.id == SensitiveWord.group_id)
        .where(SensitiveWordGroup.is_active == True)
    )
    result = await db.execute(stmt)
    word_map = {row[0]: row[1] for row in result.all()}

    # Cache
    if word_map:
        try:
            await redis_client.hset(cache_key, mapping=word_map)
        except Exception:
            pass

    return word_map


async def check_sensitive(text: str, db: AsyncSession | None = None) -> FilterResult:
    """Check text against sensitive word list.

    Returns FilterResult with action:
    - "block": contains block-level words, reject message
    - "warn": contains warn-level words, allow but flag
    - "pass": clean text
    """
    word_map = await load_sensitive_words(db)
    if not word_map:
        return FilterResult(action="pass", matched_words=[])

    matched_block = []
    matched_warn = []
    matched_review = []

    text_lower = text.lower()
    for word, level in word_map.items():
        if word.lower() in text_lower:
            if level == "block":
                matched_block.append(word)
            elif level == "warn":
                matched_warn.append(word)
            elif level == "review":
                matched_review.append(word)

    if matched_block:
        return FilterResult(
            action="block",
            matched_words=matched_block,
            message="该问题包含敏感内容，无法回答。如有疑问请联系招生办。",
        )
    if matched_warn:
        return FilterResult(
            action="warn",
            matched_words=matched_warn,
        )
    if matched_review:
        return FilterResult(
            action="warn",
            matched_words=matched_review,
        )

    return FilterResult(action="pass", matched_words=[])


async def invalidate_cache() -> None:
    """Invalidate sensitive word cache (call after admin edits)."""
    try:
        await redis_client.delete("sensitive_words:all")
    except Exception:
        pass
