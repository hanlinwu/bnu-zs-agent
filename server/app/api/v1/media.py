"""Media resource management API for administrators."""

import hashlib
import logging
import os
import subprocess

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
logger = logging.getLogger(__name__)

ALLOWED_MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "video/mp4"}
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif", "mp4"}


def _generate_image_thumbnail(image_path: str, thumb_dir: str, max_size: int = 480) -> str | None:
    """Generate a low-res JPEG thumbnail for an image."""
    base = os.path.splitext(os.path.basename(image_path))[0]
    thumb_path = os.path.join(thumb_dir, f"{base}_thumb.jpg")
    if os.path.exists(thumb_path):
        return thumb_path
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            img.thumbnail((max_size, max_size))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(thumb_path, "JPEG", quality=70)
        return thumb_path if os.path.exists(thumb_path) else None
    except Exception as e:
        logger.warning("Failed to generate image thumbnail: %s", e)
        return None


def _generate_video_thumbnail(video_path: str, thumb_dir: str) -> str | None:
    """Extract video thumbnail: prefer embedded cover art, fallback to frame at 0.5s."""
    base = os.path.splitext(os.path.basename(video_path))[0]
    thumb_path = os.path.join(thumb_dir, f"{base}_thumb.jpg")
    if os.path.exists(thumb_path):
        return thumb_path
    try:
        # Try extracting embedded cover art first
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", video_path,
                "-an", "-vcodec", "mjpeg",
                "-disposition:v", "attached_pic",
                "-frames:v", "1",
                "-vf", "scale='min(480,iw)':-2",
                thumb_path,
            ],
            capture_output=True,
            timeout=30,
            check=True,
        )
        if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
            return thumb_path
    except Exception:
        pass
    try:
        # Fallback: capture frame at 0.5s
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", "0.5",
                "-i", video_path,
                "-frames:v", "1",
                "-q:v", "5",
                "-vf", "scale='min(480,iw)':-2",
                thumb_path,
            ],
            capture_output=True,
            timeout=30,
            check=True,
        )
        return thumb_path if os.path.exists(thumb_path) else None
    except Exception as e:
        logger.warning("Failed to generate video thumbnail: %s", e)
        return None


def _media_to_dict(m: MediaResource, uploader_name: str | None = None) -> dict:
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
        "description": m.description,
        "status": m.status,
        "current_node": m.current_node or m.status or "pending",
        "current_step": m.current_step,
        "is_approved": m.is_approved,
        "uploaded_by": str(m.uploaded_by) if m.uploaded_by else None,
        "uploader_name": uploader_name,
        "reviewed_by": str(m.reviewed_by) if m.reviewed_by else None,
        "review_note": m.review_note,
        "created_at": m.created_at.isoformat(),
    }


async def _get_uploader_name(resource: MediaResource, db: AsyncSession) -> str | None:
    if not resource.uploaded_by:
        return None
    u = await db.execute(select(AdminUser.real_name).where(AdminUser.id == resource.uploaded_by))
    return u.scalar_one_or_none()


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
    stmt = (
        select(MediaResource, AdminUser.real_name)
        .outerjoin(AdminUser, MediaResource.uploaded_by == AdminUser.id)
    )
    count_stmt = select(func.count()).select_from(MediaResource)

    if media_type:
        stmt = stmt.where(MediaResource.media_type == media_type)
        count_stmt = count_stmt.where(MediaResource.media_type == media_type)
    if status:
        stmt = stmt.where(MediaResource.current_node == status)
        count_stmt = count_stmt.where(MediaResource.current_node == status)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = (
        stmt.order_by(MediaResource.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return {
        "items": [_media_to_dict(m, uploader_name) for m, uploader_name in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/upload", dependencies=[Depends(require_permission("media:create"))])
async def upload_media(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(None),
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

    # Generate thumbnail
    thumbnail_url = None
    thumb_dir = os.path.join(settings.UPLOAD_DIR, "thumbnails")
    os.makedirs(thumb_dir, exist_ok=True)
    if media_type == "video":
        thumb_path = _generate_video_thumbnail(file_path, thumb_dir)
    else:
        thumb_path = _generate_image_thumbnail(file_path, thumb_dir)
    if thumb_path:
        thumbnail_url = f"/uploads/thumbnails/{os.path.basename(thumb_path)}"

    resource = MediaResource(
        title=title,
        media_type=media_type,
        file_path=file_path,
        file_size=len(content),
        thumbnail_url=thumbnail_url,
        tags=tag_list,
        description=description or None,
        status="pending",
        current_node="pending",
        is_approved=False,
        uploaded_by=admin.id,
    )
    db.add(resource)
    await db.commit()
    await db.refresh(resource)

    return _media_to_dict(resource, admin.real_name)


class MediaUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    tags: list[str] | None = None


class MediaReviewRequest(BaseModel):
    action: str  # "approve" | "reject"
    note: str | None = None


@router.put("/{media_id}", dependencies=[Depends(require_permission("media:create"))])
async def update_media(
    media_id: str,
    body: MediaUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """编辑媒体资源信息（标题、描述、标签）"""
    result = await db.execute(select(MediaResource).where(MediaResource.id == media_id))
    resource = result.scalar_one_or_none()
    if not resource:
        raise NotFoundError("媒体资源不存在")

    if body.title is not None:
        resource.title = body.title
    if body.description is not None:
        resource.description = body.description
    if body.tags is not None:
        resource.tags = body.tags if body.tags else None

    await db.commit()
    await db.refresh(resource)

    uploader_name = await _get_uploader_name(resource, db)
    return _media_to_dict(resource, uploader_name)


@router.post("/{media_id}/review", dependencies=[Depends(require_permission("media:approve"))])
async def review_media(
    media_id: str,
    body: MediaReviewRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """审核媒体资源（执行工作流动作）"""
    result = await db.execute(select(MediaResource).where(MediaResource.id == media_id))
    resource = result.scalar_one_or_none()
    if not resource:
        raise NotFoundError("媒体资源不存在")

    current_node = resource.current_node or resource.status or "pending"

    # Use workflow service for state-machine action
    from app.services import review_workflow_service as wf_svc
    try:
        action_result = await wf_svc.execute_action(
            resource_type="media",
            resource_id=resource.id,
            current_node=current_node,
            action=body.action,
            reviewer_id=admin.id,
            note=body.note,
            db=db,
        )
    except ValueError as e:
        raise BizError(code=400, message=str(e))

    resource.current_node = action_result["new_node"]
    resource.status = action_result["new_status"]
    resource.reviewed_by = admin.id
    resource.review_note = body.note
    resource.is_approved = action_result["new_node"] == "approved"

    await db.commit()
    await db.refresh(resource)

    uploader_name = await _get_uploader_name(resource, db)
    return _media_to_dict(resource, uploader_name)


class BatchReviewRequest(BaseModel):
    ids: list[str]
    action: str
    note: str | None = None


@router.post("/batch-review", dependencies=[Depends(require_permission("media:approve"))])
async def batch_review_media(
    body: BatchReviewRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """批量审核媒体资源"""
    from app.services import review_workflow_service as wf_svc

    success_count = 0
    errors: list[str] = []

    for media_id in body.ids:
        result = await db.execute(select(MediaResource).where(MediaResource.id == media_id))
        resource = result.scalar_one_or_none()
        if not resource:
            errors.append(f"{media_id}: 资源不存在")
            continue

        current_node = resource.current_node or resource.status or "pending"
        try:
            action_result = await wf_svc.execute_action(
                resource_type="media",
                resource_id=resource.id,
                current_node=current_node,
                action=body.action,
                reviewer_id=admin.id,
                note=body.note,
                db=db,
            )
            resource.current_node = action_result["new_node"]
            resource.status = action_result["new_status"]
            resource.reviewed_by = admin.id
            resource.review_note = body.note
            resource.is_approved = action_result["new_node"] == "approved"
            success_count += 1
        except ValueError as e:
            errors.append(f"{resource.title}: {str(e)}")

    await db.commit()
    return {"success": True, "success_count": success_count, "errors": errors}


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
    if resource.thumbnail_url:
        thumb_path = os.path.join(settings.UPLOAD_DIR, resource.thumbnail_url.lstrip("/uploads/"))
        if os.path.exists(thumb_path):
            os.remove(thumb_path)

    await db.delete(resource)
    await db.commit()

    return {"success": True, "message": "媒体资源已删除"}
