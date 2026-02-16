"""Knowledge base management API with upload and review workflow."""

import hashlib
import logging
import os
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy import select, func, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db, get_session_factory
from app.core.exceptions import NotFoundError, BizError
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.models.knowledge import KnowledgeDocument, KnowledgeChunk
from app.models.audit_log import FileUploadLog
from app.schemas.knowledge import (
    KnowledgeDocResponse, KnowledgeDocListResponse,
    KnowledgeReviewRequest, ChunkPreviewResponse, ChunkListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


async def _doc_to_response(doc: KnowledgeDocument, db: AsyncSession) -> KnowledgeDocResponse:
    """Build camelCase response with uploader name and chunk count."""
    uploader_name = ""
    if doc.uploaded_by:
        admin = (await db.execute(
            select(AdminUser).where(AdminUser.id == doc.uploaded_by)
        )).scalar_one_or_none()
        if admin:
            uploader_name = admin.real_name or admin.username

    reviewer_name = None
    if doc.reviewed_by:
        reviewer = (await db.execute(
            select(AdminUser).where(AdminUser.id == doc.reviewed_by)
        )).scalar_one_or_none()
        if reviewer:
            reviewer_name = reviewer.real_name or reviewer.username

    chunk_count = (await db.execute(
        select(func.count()).select_from(KnowledgeChunk)
        .where(KnowledgeChunk.document_id == doc.id)
    )).scalar() or 0

    file_size = 0
    if doc.file_path and os.path.exists(doc.file_path):
        file_size = os.path.getsize(doc.file_path)

    return KnowledgeDocResponse(
        id=str(doc.id),
        title=doc.title,
        fileType=doc.file_type,
        fileHash=doc.file_hash or "",
        fileSize=file_size,
        status=doc.status,
        uploaderId=str(doc.uploaded_by),
        uploaderName=uploader_name,
        reviewerId=str(doc.reviewed_by) if doc.reviewed_by else None,
        reviewerName=reviewer_name,
        reviewNote=doc.review_note,
        chunkCount=chunk_count,
        createdAt=doc.created_at.isoformat(),
        updatedAt=doc.updated_at.isoformat(),
    )


@router.post("/upload", response_model=KnowledgeDocResponse,
             dependencies=[Depends(require_permission("knowledge:create"))])
async def upload_document(
    file: UploadFile = File(...),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """上传知识库文档"""
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext not in ("pdf", "docx", "txt", "md"):
        raise BizError(code=400, message="不支持的文件格式，仅支持 PDF/DOCX/TXT/MD")

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise BizError(code=400, message=f"文件大小超过 {settings.MAX_UPLOAD_SIZE_MB}MB 限制")

    file_hash = hashlib.sha256(content).hexdigest()

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = f"{settings.UPLOAD_DIR}/{file_hash}.{ext}"
    with open(file_path, "wb") as f:
        f.write(content)

    doc = KnowledgeDocument(
        title=file.filename or "untitled",
        file_type=ext,
        file_path=file_path,
        file_hash=file_hash,
        status="pending",
        uploaded_by=admin.id,
    )
    db.add(doc)

    log = FileUploadLog(
        file_name=file.filename or "untitled",
        file_hash=file_hash,
        file_type=ext,
        parse_status="pending",
    )
    db.add(log)

    await db.commit()
    await db.refresh(doc)

    return await _doc_to_response(doc, db)


@router.get("", response_model=KnowledgeDocListResponse,
            dependencies=[Depends(require_permission("knowledge:read"))])
async def list_documents(
    status: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100, alias="pageSize"),
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
    stmt = stmt.order_by(KnowledgeDocument.created_at.desc()).offset((page - 1) * pageSize).limit(pageSize)
    result = await db.execute(stmt)
    docs = result.scalars().all()

    return KnowledgeDocListResponse(
        items=[await _doc_to_response(d, db) for d in docs],
        total=total, page=page, pageSize=pageSize,
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
    return await _doc_to_response(doc, db)


@router.get("/{doc_id}/download",
            dependencies=[Depends(require_permission("knowledge:read"))])
async def download_document(
    doc_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """下载文档原文件"""
    doc = await _get_document(doc_id, db)

    if not doc.file_path or not os.path.exists(doc.file_path):
        raise NotFoundError("文件不存在或已被删除")

    # Encode filename for Content-Disposition header (RFC 5987)
    encoded_name = quote(doc.title)
    return FileResponse(
        path=doc.file_path,
        filename=doc.title,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
        },
    )


@router.get("/{doc_id}/chunks", response_model=ChunkListResponse,
            dependencies=[Depends(require_permission("knowledge:read"))])
async def get_document_chunks(
    doc_id: str,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100, alias="pageSize"),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """文档切片预览（分页）"""
    await _get_document(doc_id, db)

    total = (await db.execute(
        select(func.count()).select_from(KnowledgeChunk)
        .where(KnowledgeChunk.document_id == doc_id)
    )).scalar() or 0

    result = await db.execute(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.document_id == doc_id)
        .order_by(KnowledgeChunk.chunk_index)
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    )
    chunks = result.scalars().all()
    return ChunkListResponse(
        items=[
            ChunkPreviewResponse(
                id=str(c.id), chunkIndex=c.chunk_index,
                content=c.content, tokenCount=c.token_count,
            )
            for c in chunks
        ],
        total=total, page=page, pageSize=pageSize,
    )


@router.post("/{doc_id}/review", response_model=KnowledgeDocResponse,
             dependencies=[Depends(require_permission("knowledge:approve"))])
async def review_document(
    doc_id: str,
    body: KnowledgeReviewRequest,
    background_tasks: BackgroundTasks,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """审核通过/拒绝"""
    doc = await _get_document(doc_id, db)

    if doc.status not in ("pending", "reviewing"):
        raise BizError(code=400, message=f"当前状态 '{doc.status}' 不允许审核操作")

    # Use workflow service for multi-step review
    from app.services import review_workflow_service as wf_svc
    review_result = await wf_svc.submit_review(
        resource_type="knowledge",
        resource_id=doc.id,
        current_step=doc.current_step,
        action=body.action,
        reviewer_id=admin.id,
        note=body.note,
        db=db,
    )

    doc.reviewed_by = admin.id
    doc.review_note = body.note
    doc.updated_at = datetime.now(timezone.utc)
    doc.current_step = review_result["new_step"]

    if review_result["new_status"] == "approved" or (body.action == "approve" and review_result["is_final"]):
        doc.status = "processing"
        doc.effective_from = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(doc)

        # Run chunking in background so the response returns immediately
        background_tasks.add_task(
            _background_chunk_document,
            str(doc.id), doc.file_path, doc.file_type,
        )
    else:
        doc.status = review_result["new_status"]
        await db.commit()
        await db.refresh(doc)

    return await _doc_to_response(doc, db)


async def _background_chunk_document(doc_id: str, file_path: str, file_type: str):
    """Background task: parse file, create chunks, update status."""
    session_factory = get_session_factory()
    async with session_factory() as db:
        try:
            from app.services.file_parser_service import parse_file, chunk_text

            text = parse_file(file_path, file_type)
            text_chunks = chunk_text(text)

            # Remove old chunks if re-approving
            await db.execute(
                sql_delete(KnowledgeChunk)
                .where(KnowledgeChunk.document_id == doc_id)
            )

            # Create chunk records
            for idx, chunk_content in enumerate(text_chunks):
                chunk = KnowledgeChunk(
                    document_id=doc_id,
                    chunk_index=idx,
                    content=chunk_content,
                    token_count=len(chunk_content),
                )
                db.add(chunk)

            # Update document status to approved
            doc = (await db.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
            )).scalar_one()
            doc.status = "approved"
            doc.updated_at = datetime.now(timezone.utc)

            await db.commit()
            logger.info("Document %s chunked: %d chunks", doc_id, len(text_chunks))

            # Trigger async embedding generation if configured
            if settings.EMBEDDING_BASE_URL or settings.LLM_PRIMARY_BASE_URL:
                try:
                    from app.tasks.embedding_task import generate_embeddings_task
                    generate_embeddings_task.delay(doc_id, text_chunks)
                except Exception as e:
                    logger.warning("Failed to queue embedding task: %s", e)

        except Exception as e:
            logger.error("Failed to chunk document %s: %s", doc_id, e)
            # Mark document as failed so the admin can see the error
            try:
                doc = (await db.execute(
                    select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
                )).scalar_one()
                doc.status = "pending"
                doc.review_note = f"切片失败: {str(e)}"
                doc.updated_at = datetime.now(timezone.utc)
                await db.commit()
            except Exception:
                logger.error("Failed to update document status after chunk error")


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
