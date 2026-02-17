"""Media matching service for chat visual responses."""

from __future__ import annotations

import os
import re
from typing import Any

from sqlalchemy import or_, select, String, cast
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import MediaResource


VISUAL_HINT_KEYWORDS = [
    "校园", "环境", "风景", "宿舍", "食堂", "图书馆", "实验室", "教学楼", "操场", "体育馆", "校门", "校园生活",
    "图片", "照片", "图像", "视频", "看看", "看一下", "看看学校", "校园长什么样",
]


def is_visual_query(question: str) -> bool:
    text = (question or "").lower()
    if not text:
        return False
    return any(keyword in text for keyword in VISUAL_HINT_KEYWORDS)


def extract_query_keywords(question: str) -> list[str]:
    text = (question or "").strip().lower()
    if not text:
        return []

    matched_domain_keywords = [kw for kw in VISUAL_HINT_KEYWORDS if kw in text and len(kw) >= 2]

    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9]{2,}", text)
    stopwords = {
        "请问", "可以", "这个", "那个", "一下", "一下子", "学校", "校园", "环境", "图片", "视频", "照片",
        "什么", "怎么", "有没有", "看看", "看下", "一下",
    }
    uniq: list[str] = []
    for token in matched_domain_keywords:
        if token not in uniq:
            uniq.append(token)

    for token in tokens:
        if token in stopwords:
            continue
        if token not in uniq:
            uniq.append(token)
    return uniq[:8]


def _score_media(item: MediaResource, keywords: list[str], question: str) -> int:
    haystack_parts = [item.title or "", item.description or "", " ".join(item.tags or [])]
    haystack = " ".join(haystack_parts).lower()

    score = 0
    for kw in keywords:
        if kw in haystack:
            score += 2

    q = (question or "").lower()
    if "视频" in q and item.media_type == "video":
        score += 2
    if ("图片" in q or "照片" in q or "图像" in q) and item.media_type == "image":
        score += 2

    return score


async def match_media_for_question(
    question: str,
    db: AsyncSession,
    *,
    limit: int = 4,
    preferred_tags: list[str] | None = None,
    exclude_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    if not is_visual_query(question):
        return []

    keywords = extract_query_keywords(question)
    if preferred_tags:
        for tag in preferred_tags:
            normalized = (tag or "").strip().lower()
            if normalized and normalized not in keywords:
                keywords.append(normalized)
    approved_filter = or_(
        MediaResource.is_approved == True,
        MediaResource.current_node == "approved",
        MediaResource.status == "approved",
    )

    stmt = select(MediaResource).where(
        or_(
            MediaResource.is_approved == True,
            MediaResource.current_node == "approved",
            MediaResource.status == "approved",
        )
    )

    if keywords:
        like_conditions = []
        for kw in keywords:
            pattern = f"%{kw}%"
            like_conditions.extend([
                MediaResource.title.ilike(pattern),
                MediaResource.description.ilike(pattern),
                cast(MediaResource.tags, String).ilike(pattern),
            ])
        stmt = stmt.where(or_(*like_conditions))

    stmt = stmt.order_by(MediaResource.created_at.desc()).limit(80)
    result = await db.execute(stmt)
    candidates = result.scalars().all()
    excluded = exclude_ids or set()
    if excluded:
        candidates = [item for item in candidates if str(item.id) not in excluded]

    scored = []
    for item in candidates:
        score = _score_media(item, keywords, question)
        if keywords and score <= 0:
            continue
        scored.append((score, item))

    scored.sort(key=lambda row: row[0], reverse=True)
    selected = [item for _, item in scored[:limit]]

    # Fallback: visual query but no keyword match -> return latest approved media
    if not selected:
        fallback_stmt = (
            select(MediaResource)
            .where(approved_filter)
            .order_by(MediaResource.created_at.desc())
            .limit(limit)
        )
        fallback_res = await db.execute(fallback_stmt)
        selected = [item for item in fallback_res.scalars().all() if str(item.id) not in excluded]

    media_items: list[dict[str, Any]] = []
    for item in selected:
        basename = os.path.basename(item.file_path) if item.file_path else ""
        file_url = f"/uploads/media/{basename}" if basename else ""
        media_items.append(
            {
                "id": str(item.id),
                "media_type": item.media_type,
                "url": file_url,
                "title": item.title,
                "description": item.description,
                "tags": item.tags or [],
            }
        )

    return media_items
