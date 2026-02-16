"""Media resource management API for administrators."""

import hashlib
import os

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from pydantic import BaseModel
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


def _media_to_dict(m: MediaResource) -> dict:
    """Build response dict for a media resource."""
    file_url = ""
    if m.file_path:
        basename = os.path.basename(m.file_path)
        file_url = f"/uploads/media/{basename}"
    return {
        "id": str(m.id),
        "title": m.title,
        "media_type": m.media_type,
        "file_url": file_url,
        "file_size": m.file_size,
        "thumbnail_url": m.thumbnail_url,
        "tags": m.tags or [],
        "source": m.source,
        "status": m.status,
        "current_step": m.current_step,
        "is_approved": m.is_approved,
        "uploaded_by": str(m.uploaded_by) if m.uploaded_by else None,
        "reviewed_by": str(m.reviewed_by) if m.reviewed_by else None,
        "review_note": m.review_note,
        "created_at": m.created_at.isoformat(),
    }


@router.get("", dependencies=[Depends(require_permission("media:read"))])
async def list_media(
    media_type: str | None = None,
    status: str | None = None,
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
    if status:
        stmt = stmt.where(MediaResource.status == status)
        count_stmt = count_stmt.where(MediaResource.status == status)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = (
        stmt.order_by(MediaResource.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    return {
        "items": [_media_to_dict(m) for m in items],
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
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise BizError(code=400, message=f"不支持的文件格式，仅支持: {', '.join(ALLOWED_EXTENSIONS)}")

    if file.content_type and file.content_type not in ALLOWED_MEDIA_TYPES:
        raise BizError(code=400, message="不支持的媒体类型")

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise BizError(code=400, message=f"文件大小超过 {settings.MAX_UPLOAD_SIZE_MB}MB 限制")

    file_hash = hashlib.sha256(content).hexdigest()
    media_type = "image" if ext in {"jpg", "jpeg", "png", "webp", "gif"} else "video"

    media_dir = os.path.join(settings.UPLOAD_DIR, "media")
    os.makedirs(media_dir, exist_ok=True)
    file_path = os.path.join(media_dir, f"{file_hash}.{ext}")
    with open(file_path, "wb") as f:
        f.write(content)

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    resource = MediaResource(
        title=title,
        media_type=media_type,
        file_path=file_path,
        file_size=len(content),
        tags=tag_list,
        source=source,
        status="pending",
        is_approved=False,
        uploaded_by=admin.id,
    )
    db.add(resource)
    await db.commit()
    await db.refresh(resource)

    return _media_to_dict(resource)


class MediaReviewRequest(BaseModel):
    action: str  # "approve" | "reject"
    note: str | None = None


@router.post("/{media_id}/review", dependencies=[Depends(require_permission("media:approve"))])
async def review_media(
    media_id: str,
    body: MediaReviewRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """审核媒体资源（通过/拒绝）"""
    result = await db.execute(select(MediaResource).where(MediaResource.id == media_id))
    resource = result.scalar_one_or_none()
    if not resource:
        raise NotFoundError("媒体资源不存在")

    if resource.status not in ("pending", "reviewing"):
        raise BizError(code=400, message=f"当前状态 '{resource.status}' 不允许审核操作")

    if body.action not in ("approve", "reject"):
        raise BizError(code=400, message="action 必须为 approve 或 reject")

    # Use workflow service for multi-step review
    from app.services import review_workflow_service as wf_svc
    review_result = await wf_svc.submit_review(
        resource_type="media",
        resource_id=resource.id,
        current_step=resource.current_step,
        action=body.action,
        reviewer_id=admin.id,
        note=body.note,
        db=db,
    )

    resource.status = review_result["new_status"]
    resource.current_step = review_result["new_step"]
    resource.reviewed_by = admin.id
    resource.review_note = body.note
    resource.is_approved = review_result["new_status"] == "approved"

    await db.commit()
    await db.refresh(resource)

    return _media_to_dict(resource)


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

    if os.path.exists(resource.file_path):
        os.remove(resource.file_path)

    await db.delete(resource)
    await db.commit()

    return {"success": True, "message": "媒体资源已删除"}
