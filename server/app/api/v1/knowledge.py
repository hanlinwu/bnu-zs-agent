"""Knowledge base management API with upload and review workflow."""

import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.core.exceptions import NotFoundError, BizError
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.models.knowledge import KnowledgeDocument, KnowledgeChunk
from app.models.audit_log import FileUploadLog
from app.schemas.knowledge import (
    KnowledgeDocResponse, KnowledgeDocListResponse,
    KnowledgeReviewRequest, ChunkPreviewResponse,
)

router = APIRouter()


@router.post("/upload", response_model=KnowledgeDocResponse,
             dependencies=[Depends(require_permission("knowledge:create"))])
async def upload_document(
    file: UploadFile = File(...),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """上传知识库文档"""
    # Validate file type
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext not in ("pdf", "docx", "txt", "md"):
        raise BizError(code=400, message="不支持的文件格式，仅支持 PDF/DOCX/TXT/MD")

    # Read and hash file
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise BizError(code=400, message=f"文件大小超过 {settings.MAX_UPLOAD_SIZE_MB}MB 限制")

    file_hash = hashlib.sha256(content).hexdigest()

    # Save file
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = f"{settings.UPLOAD_DIR}/{file_hash}.{ext}"
    with open(file_path, "wb") as f:
        f.write(content)

    # Create document record
    doc = KnowledgeDocument(
        title=file.filename or "untitled",
        file_type=ext,
        file_path=file_path,
        file_hash=file_hash,
        status="pending",
        uploaded_by=admin.id,
    )
    db.add(doc)

    # Create file upload log
    log = FileUploadLog(
        file_name=file.filename or "untitled",
        file_hash=file_hash,
        file_type=ext,
        parse_status="pending",
    )
    db.add(log)

    await db.commit()
    await db.refresh(doc)

    return _doc_to_response(doc)


@router.get("", response_model=KnowledgeDocListResponse,
            dependencies=[Depends(require_permission("knowledge:read"))])
async def list_documents(
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """文档列表（分页筛选）"""
    stmt = select(KnowledgeDocument)
    count_stmt = select(func.count()).select_from(KnowledgeDocument)

    if status:
        stmt = stmt.where(KnowledgeDocument.status == status)
        count_stmt = count_stmt.where(KnowledgeDocument.status == status)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(KnowledgeDocument.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    docs = result.scalars().all()

    return KnowledgeDocListResponse(
        items=[_doc_to_response(d) for d in docs],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{doc_id}", response_model=KnowledgeDocResponse,
            dependencies=[Depends(require_permission("knowledge:read"))])
async def get_document(
    doc_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """文档详情"""
    doc = await _get_document(doc_id, db)
    return _doc_to_response(doc)


@router.get("/{doc_id}/chunks", response_model=list[ChunkPreviewResponse],
            dependencies=[Depends(require_permission("knowledge:read"))])
async def get_document_chunks(
    doc_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """文档切片预览"""
    await _get_document(doc_id, db)
    result = await db.execute(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.document_id == doc_id)
        .order_by(KnowledgeChunk.chunk_index)
    )
    chunks = result.scalars().all()
    return [
        ChunkPreviewResponse(
            id=str(c.id), chunk_index=c.chunk_index,
            content=c.content, token_count=c.token_count,
        )
        for c in chunks
    ]


@router.post("/{doc_id}/review", response_model=KnowledgeDocResponse,
             dependencies=[Depends(require_permission("knowledge:approve"))])
async def review_document(
    doc_id: str,
    body: KnowledgeReviewRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """审核通过/拒绝"""
    doc = await _get_document(doc_id, db)

    if doc.status not in ("pending", "reviewing"):
        raise BizError(code=400, message=f"当前状态 '{doc.status}' 不允许审核操作")

    doc.reviewed_by = admin.id
    doc.review_note = body.note
    doc.updated_at = datetime.now(timezone.utc)

    if body.action == "approve":
        doc.status = "approved"
        doc.effective_from = datetime.now(timezone.utc)
        # Trigger parsing + embedding pipeline via Celery
        # from app.tasks.parse_task import parse_document
        # parse_document.delay(str(doc.id), doc.file_path, doc.file_type)
    else:
        doc.status = "rejected"

    await db.commit()
    await db.refresh(doc)
    return _doc_to_response(doc)


@router.delete("/{doc_id}", dependencies=[Depends(require_permission("knowledge:delete"))])
async def archive_document(
    doc_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """归档文档"""
    doc = await _get_document(doc_id, db)
    doc.status = "archived"
    doc.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True, "message": "文档已归档"}


async def _get_document(doc_id: str, db: AsyncSession) -> KnowledgeDocument:
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("文档不存在")
    return doc


def _doc_to_response(doc: KnowledgeDocument) -> KnowledgeDocResponse:
    return KnowledgeDocResponse(
        id=str(doc.id),
        title=doc.title,
        file_type=doc.file_type,
        status=doc.status,
        uploaded_by=str(doc.uploaded_by),
        reviewed_by=str(doc.reviewed_by) if doc.reviewed_by else None,
        review_note=doc.review_note,
        created_at=doc.created_at.isoformat(),
        updated_at=doc.updated_at.isoformat(),
    )
