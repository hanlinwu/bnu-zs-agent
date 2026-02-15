"""Media resource management API for administrators."""

import hashlib
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.core.exceptions import NotFoundError, BizError
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.models.media import MediaResource

router = APIRouter()

ALLOWED_MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "video/mp4"}
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif", "mp4"}


@router.get("", dependencies=[Depends(require_permission("media:read"))])
async def list_media(
    media_type: str | None = None,
    is_approved: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """媒体资源列表（分页、筛选）"""
    stmt = select(MediaResource)
    count_stmt = select(func.count()).select_from(MediaResource)

    if media_type:
        stmt = stmt.where(MediaResource.media_type == media_type)
        count_stmt = count_stmt.where(MediaResource.media_type == media_type)
    if is_approved is not None:
        stmt = stmt.where(MediaResource.is_approved == is_approved)
        count_stmt = count_stmt.where(MediaResource.is_approved == is_approved)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = (
        stmt.order_by(MediaResource.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    return {
        "items": [
            {
                "id": str(m.id),
                "title": m.title,
                "media_type": m.media_type,
                "file_path": m.file_path,
                "thumbnail_url": m.thumbnail_url,
                "tags": m.tags,
                "source": m.source,
                "is_approved": m.is_approved,
                "uploaded_by": str(m.uploaded_by) if m.uploaded_by else None,
                "created_at": m.created_at.isoformat(),
            }
            for m in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/upload", dependencies=[Depends(require_permission("media:create"))])
async def upload_media(
    file: UploadFile = File(...),
    title: str = Form(...),
    source: str = Form(None),
    tags: str = Form(None),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """上传媒体资源（仅限官方素材）"""
    # Validate file extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise BizError(code=400, message=f"不支持的文件格式，仅支持: {', '.join(ALLOWED_EXTENSIONS)}")

    # Validate content type
    if file.content_type and file.content_type not in ALLOWED_MEDIA_TYPES:
        raise BizError(code=400, message="不支持的媒体类型")

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise BizError(code=400, message=f"文件大小超过 {settings.MAX_UPLOAD_SIZE_MB}MB 限制")

    file_hash = hashlib.sha256(content).hexdigest()

    # Determine media type category
    media_type = "image" if ext in {"jpg", "jpeg", "png", "webp", "gif"} else "video"

    # Save file
    media_dir = os.path.join(settings.UPLOAD_DIR, "media")
    os.makedirs(media_dir, exist_ok=True)
    file_path = os.path.join(media_dir, f"{file_hash}.{ext}")
    with open(file_path, "wb") as f:
        f.write(content)

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    resource = MediaResource(
        title=title,
        media_type=media_type,
        file_path=file_path,
        tags=tag_list,
        source=source,
        is_approved=False,
        uploaded_by=admin.id,
    )
    db.add(resource)
    await db.commit()
    await db.refresh(resource)

    return {
        "id": str(resource.id),
        "title": resource.title,
        "media_type": resource.media_type,
        "file_path": resource.file_path,
        "tags": resource.tags,
        "source": resource.source,
        "is_approved": resource.is_approved,
        "created_at": resource.created_at.isoformat(),
    }


@router.put("/{media_id}/approve", dependencies=[Depends(require_permission("media:approve"))])
async def approve_media(
    media_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """审批通过媒体资源"""
    result = await db.execute(select(MediaResource).where(MediaResource.id == media_id))
    resource = result.scalar_one_or_none()
    if not resource:
        raise NotFoundError("媒体资源不存在")

    if resource.is_approved:
        raise BizError(code=400, message="该资源已审批通过")

    resource.is_approved = True
    await db.commit()

    return {"success": True, "message": "媒体资源已审批通过"}


@router.delete("/{media_id}", dependencies=[Depends(require_permission("media:delete"))])
async def delete_media(
    media_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除媒体资源"""
    result = await db.execute(select(MediaResource).where(MediaResource.id == media_id))
    resource = result.scalar_one_or_none()
    if not resource:
        raise NotFoundError("媒体资源不存在")

    # Remove file from disk
    if os.path.exists(resource.file_path):
        os.remove(resource.file_path)

    await db.delete(resource)
    await db.commit()

    return {"success": True, "message": "媒体资源已删除"}
