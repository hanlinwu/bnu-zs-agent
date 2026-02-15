"""Sensitive word management API for administrators."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.models.sensitive_word import SensitiveWordGroup, SensitiveWord

router = APIRouter()


class GroupCreateRequest(BaseModel):
    name: str
    description: str | None = None
    is_active: bool = True


class WordCreateRequest(BaseModel):
    group_id: str
    word: str
    level: str = "block"


@router.get("/groups", dependencies=[Depends(require_permission("sensitive:read"))])
async def list_groups(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """敏感词组列表"""
    result = await db.execute(select(SensitiveWordGroup).order_by(SensitiveWordGroup.created_at))
    groups = result.scalars().all()

    items = []
    for g in groups:
        word_count = (
            await db.execute(
                select(func.count()).select_from(SensitiveWord).where(SensitiveWord.group_id == g.id)
            )
        ).scalar() or 0
        items.append({
            "id": str(g.id),
            "name": g.name,
            "description": g.description,
            "is_active": g.is_active,
            "word_count": word_count,
            "created_at": g.created_at.isoformat(),
        })

    return {"items": items}


@router.post("/groups", dependencies=[Depends(require_permission("sensitive:create"))])
async def create_group(
    body: GroupCreateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建敏感词组"""
    group = SensitiveWordGroup(
        name=body.name,
        description=body.description,
        is_active=body.is_active,
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)

    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "is_active": group.is_active,
        "created_at": group.created_at.isoformat(),
    }


@router.get("/groups/{group_id}", dependencies=[Depends(require_permission("sensitive:read"))])
async def get_group_detail(
    group_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """敏感词组详情 + 词条列表"""
    result = await db.execute(select(SensitiveWordGroup).where(SensitiveWordGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise NotFoundError("敏感词组不存在")

    # Paginated word list
    count_stmt = (
        select(func.count()).select_from(SensitiveWord).where(SensitiveWord.group_id == group.id)
    )
    total = (await db.execute(count_stmt)).scalar() or 0

    word_stmt = (
        select(SensitiveWord)
        .where(SensitiveWord.group_id == group.id)
        .order_by(SensitiveWord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    words_result = await db.execute(word_stmt)
    words = words_result.scalars().all()

    return {
        "group": {
            "id": str(group.id),
            "name": group.name,
            "description": group.description,
            "is_active": group.is_active,
            "created_at": group.created_at.isoformat(),
        },
        "words": {
            "items": [
                {
                    "id": str(w.id),
                    "word": w.word,
                    "level": w.level,
                    "created_at": w.created_at.isoformat(),
                }
                for w in words
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.post("/words", dependencies=[Depends(require_permission("sensitive:create"))])
async def add_word(
    body: WordCreateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """向词组添加敏感词"""
    # Verify group exists
    result = await db.execute(
        select(SensitiveWordGroup).where(SensitiveWordGroup.id == body.group_id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("敏感词组不存在")

    word = SensitiveWord(
        group_id=body.group_id,
        word=body.word,
        level=body.level,
    )
    db.add(word)
    await db.commit()
    await db.refresh(word)

    return {
        "id": str(word.id),
        "group_id": str(word.group_id),
        "word": word.word,
        "level": word.level,
        "created_at": word.created_at.isoformat(),
    }


@router.delete("/words/{word_id}", dependencies=[Depends(require_permission("sensitive:delete"))])
async def delete_word(
    word_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除敏感词"""
    result = await db.execute(select(SensitiveWord).where(SensitiveWord.id == word_id))
    word = result.scalar_one_or_none()
    if not word:
        raise NotFoundError("敏感词不存在")

    await db.delete(word)
    await db.commit()

    return {"success": True, "message": "敏感词已删除"}
