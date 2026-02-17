"""Sensitive word management API for administrators."""

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select, func, delete, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError, BadRequestError
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.models.sensitive_word import SensitiveWordGroup, SensitiveWord
from app.services.sensitive_service import invalidate_cache

router = APIRouter()


def _parse_word_list(word_list: str | None) -> list[str]:
    """Parse word_list text into deduplicated words (keep original order)."""
    if not word_list:
        return []

    words: list[str] = []
    seen: set[str] = set()
    for line in word_list.splitlines():
        word = line.strip()
        if not word or word.startswith("#"):
            continue
        if word not in seen:
            seen.add(word)
            words.append(word)
    return words


class GroupCreateRequest(BaseModel):
    name: str
    description: str | None = None
    level: str = "block"  # block, warn, review
    word_list: str | None = None  # 文本格式，每行一个词
    is_active: bool = True


class GroupUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    level: str | None = None
    word_list: str | None = None
    is_active: bool | None = None


class WordListUpdateRequest(BaseModel):
    word_list: str  # 文本格式，每行一个词


async def _sync_word_list_to_records(
    db: AsyncSession, group_id: str, word_list: str | None, level: str
) -> int:
    """将 word_list 同步到 SensitiveWord 记录表中（用于兼容现有服务）"""
    # 先删除该组的所有现有记录
    await db.execute(
        delete(SensitiveWord).where(SensitiveWord.group_id == group_id)
    )

    words = _parse_word_list(word_list)
    if not words:
        return 0

    rows = [{"group_id": group_id, "word": word, "level": level} for word in words]
    await db.execute(insert(SensitiveWord), rows)
    return len(words)


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
        # 计算词数量（从 word_list 或关联记录）
        if g.word_list:
            word_count = len([w for w in g.word_list.split("\n") if w.strip()])
        else:
            word_count = (
                await db.execute(
                    select(func.count()).select_from(SensitiveWord).where(SensitiveWord.group_id == g.id)
                )
            ).scalar() or 0

        items.append({
            "id": str(g.id),
            "name": g.name,
            "description": g.description,
            "level": g.level,
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
        level=body.level,
        word_list=body.word_list,
        is_active=body.is_active,
    )
    db.add(group)
    await db.flush()

    # 同步到 SensitiveWord 表（用于兼容现有服务）
    await _sync_word_list_to_records(db, str(group.id), body.word_list, body.level)
    await db.commit()
    await db.refresh(group)

    # 清除缓存
    await invalidate_cache()

    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "level": group.level,
        "word_list": group.word_list,
        "is_active": group.is_active,
        "created_at": group.created_at.isoformat(),
    }


@router.get("/groups/{group_id}", dependencies=[Depends(require_permission("sensitive:read"))])
async def get_group_detail(
    group_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """敏感词组详情（包含 word_list 文本）"""
    result = await db.execute(select(SensitiveWordGroup).where(SensitiveWordGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise NotFoundError("敏感词组不存在")

    # 计算词数量
    if group.word_list:
        word_count = len([w for w in group.word_list.split("\n") if w.strip()])
    else:
        word_count = (
            await db.execute(
                select(func.count()).select_from(SensitiveWord).where(SensitiveWord.group_id == group.id)
            )
        ).scalar() or 0

    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "level": group.level,
        "word_list": group.word_list or "",
        "is_active": group.is_active,
        "word_count": word_count,
        "created_at": group.created_at.isoformat(),
    }


@router.put("/groups/{group_id}", dependencies=[Depends(require_permission("sensitive:update"))])
async def update_group(
    group_id: str,
    body: GroupUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新敏感词组"""
    result = await db.execute(select(SensitiveWordGroup).where(SensitiveWordGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise NotFoundError("敏感词组不存在")

    if body.name is not None:
        group.name = body.name
    if body.description is not None:
        group.description = body.description
    if body.level is not None:
        group.level = body.level
    if body.word_list is not None:
        group.word_list = body.word_list
    if body.is_active is not None:
        group.is_active = body.is_active

    # 同步到 SensitiveWord 表
    await _sync_word_list_to_records(db, group_id, group.word_list, group.level)
    await db.commit()
    await db.refresh(group)

    # 清除缓存
    await invalidate_cache()

    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "level": group.level,
        "word_list": group.word_list or "",
        "is_active": group.is_active,
        "created_at": group.created_at.isoformat(),
    }


@router.delete("/groups/{group_id}", dependencies=[Depends(require_permission("sensitive:delete"))])
async def delete_group(
    group_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除敏感词组"""
    result = await db.execute(select(SensitiveWordGroup).where(SensitiveWordGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise NotFoundError("敏感词组不存在")

    await db.delete(group)
    await db.commit()

    # 清除缓存
    await invalidate_cache()

    return {"success": True, "message": "敏感词组已删除"}


@router.post("/groups/upload", dependencies=[Depends(require_permission("sensitive:create"))])
async def upload_word_file(
    name: str = Form(...),
    level: str = Form("block"),
    description: str | None = Form(None),
    file: UploadFile = File(...),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """上传txt文件创建敏感词组

    文件格式：每行一个敏感词
    """
    # 验证文件类型
    if not file.filename or not file.filename.endswith(".txt"):
        raise BadRequestError("只支持上传 .txt 文件")

    # 读取文件内容
    content = await file.read()
    try:
        word_list = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            word_list = content.decode("gbk")
        except UnicodeDecodeError:
            raise BadRequestError("文件编码不支持，请使用 UTF-8 或 GBK 编码")

    # 创建词组
    group = SensitiveWordGroup(
        name=name,
        description=description,
        level=level,
        word_list=word_list,
        is_active=True,
    )
    db.add(group)
    await db.flush()

    # 同步到 SensitiveWord 表
    await _sync_word_list_to_records(db, str(group.id), word_list, level)
    await db.commit()
    await db.refresh(group)

    # 清除缓存
    await invalidate_cache()

    word_count = len(_parse_word_list(word_list))

    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "level": group.level,
        "word_count": word_count,
        "created_at": group.created_at.isoformat(),
    }


# 保留旧API以保持兼容性（可选，建议后续移除）
@router.get("/groups/{group_id}/words", dependencies=[Depends(require_permission("sensitive:read"))])
async def get_group_words(
    group_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取敏感词组中的词列表（从 word_list 解析）"""
    result = await db.execute(select(SensitiveWordGroup).where(SensitiveWordGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise NotFoundError("敏感词组不存在")

    # 从 word_list 解析
    if group.word_list:
        all_words = [w.strip() for w in group.word_list.split("\n") if w.strip()]
    else:
        # 兼容旧数据，从 SensitiveWord 表读取
        word_stmt = (
            select(SensitiveWord)
            .where(SensitiveWord.group_id == group_id)
            .order_by(SensitiveWord.created_at.desc())
        )
        words_result = await db.execute(word_stmt)
        all_words = [w.word for w in words_result.scalars().all()]

    total = len(all_words)
    start = (page - 1) * page_size
    end = start + page_size
    items = all_words[start:end]

    return {
        "items": [{"word": w, "level": group.level} for w in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
