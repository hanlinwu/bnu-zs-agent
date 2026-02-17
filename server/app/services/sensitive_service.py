"""Sensitive word filtering service with Redis caching."""

import asyncio
import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_client
from app.models.sensitive_word import SensitiveWord, SensitiveWordGroup

logger = logging.getLogger(__name__)

try:
    import ahocorasick  # type: ignore
except Exception:  # pragma: no cover
    ahocorasick = None


CACHE_KEY = "sensitive_words:all"
VERSION_KEY = "sensitive_words:version"

LEVEL_PRIORITY = {
    "warn": 1,
    "review": 2,
    "block": 3,
}


def _higher_level(left: str, right: str) -> str:
    return left if LEVEL_PRIORITY.get(left, 0) >= LEVEL_PRIORITY.get(right, 0) else right


_matcher_lock = asyncio.Lock()
_matcher_version = ""
_matcher: object | None = None
_matcher_type = "scan"


@dataclass
class FilterResult:
    action: str  # "pass" | "warn" | "block"
    matched_words: list[str]
    message: str | None = None
    highest_level: str | None = None


async def load_sensitive_words(db: AsyncSession | None = None) -> dict[str, str]:
    """Load all active sensitive words into Redis cache.
    Returns dict of word -> level.
    """
    # Try cache first
    try:
        cached = await redis_client.hgetall(CACHE_KEY)
        if cached:
            try:
                await redis_client.setnx(VERSION_KEY, "1")
            except Exception:
                pass
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
            await redis_client.hset(CACHE_KEY, mapping=word_map)
            await redis_client.setnx(VERSION_KEY, "1")
        except Exception:
            pass

    return word_map


def _build_matcher(word_map: dict[str, str]) -> tuple[str, object]:
    normalized_map: dict[str, str] = {}
    for word, level in word_map.items():
        normalized = (word or "").strip().lower()
        if not normalized:
            continue
        if normalized in normalized_map:
            normalized_map[normalized] = _higher_level(normalized_map[normalized], level)
        else:
            normalized_map[normalized] = level

    if ahocorasick is not None:
        automaton = ahocorasick.Automaton()
        for word, level in normalized_map.items():
            automaton.add_word(word, (word, level))
        automaton.make_automaton()
        return "aho", automaton

    return "scan", list(normalized_map.items())


async def _get_version() -> str:
    try:
        version = await redis_client.get(VERSION_KEY)
        return version or "0"
    except Exception:
        return "0"


async def _get_matcher(word_map: dict[str, str]) -> tuple[str, object]:
    global _matcher_version, _matcher, _matcher_type

    version = await _get_version()
    if version == "0":
        return _build_matcher(word_map)

    if _matcher is not None and _matcher_version == version:
        return _matcher_type, _matcher

    async with _matcher_lock:
        version = await _get_version()
        if _matcher is not None and _matcher_version == version:
            return _matcher_type, _matcher

        matcher_type, matcher = _build_matcher(word_map)
        _matcher_type = matcher_type
        _matcher = matcher
        _matcher_version = version
        return matcher_type, matcher


def _match_words(text: str, matcher_type: str, matcher: object) -> tuple[list[str], list[str], list[str]]:
    text_lower = text.lower()
    matched_block: set[str] = set()
    matched_warn: set[str] = set()
    matched_review: set[str] = set()

    if matcher_type == "aho":
        for _, (word, level) in matcher.iter(text_lower):  # type: ignore[attr-defined]
            if level == "block":
                matched_block.add(word)
            elif level == "warn":
                matched_warn.add(word)
            elif level == "review":
                matched_review.add(word)
    else:
        for word, level in matcher:  # type: ignore[assignment]
            if word in text_lower:
                if level == "block":
                    matched_block.add(word)
                elif level == "warn":
                    matched_warn.add(word)
                elif level == "review":
                    matched_review.add(word)

    return sorted(matched_block), sorted(matched_warn), sorted(matched_review)


async def check_sensitive(text: str, db: AsyncSession | None = None) -> FilterResult:
    """Check text against sensitive word list.

    Returns FilterResult with action:
    - "block": contains block-level words, reject message
    - "warn": contains warn-level words, allow but flag
    - "pass": clean text
    """
    word_map = await load_sensitive_words(db)
    if not word_map:
        return FilterResult(action="pass", matched_words=[], highest_level=None)

    matcher_type, matcher = await _get_matcher(word_map)
    matched_block, matched_warn, matched_review = _match_words(text, matcher_type, matcher)

    if matched_block:
        return FilterResult(
            action="block",
            matched_words=matched_block,
            message="该问题包含敏感内容，无法回答。如有疑问请联系招生办。",
            highest_level="block",
        )
    if matched_warn:
        return FilterResult(
            action="warn",
            matched_words=matched_warn,
            highest_level="warn",
        )
    if matched_review:
        return FilterResult(
            action="warn",
            matched_words=matched_review,
            highest_level="review",
        )

    return FilterResult(action="pass", matched_words=[], highest_level=None)


async def invalidate_cache() -> None:
    """Invalidate sensitive word cache (call after admin edits)."""
    global _matcher_version, _matcher, _matcher_type

    try:
        await redis_client.delete(CACHE_KEY)
        await redis_client.incr(VERSION_KEY)
    except Exception:
        pass

    _matcher_version = ""
    _matcher = None
    _matcher_type = "scan"
