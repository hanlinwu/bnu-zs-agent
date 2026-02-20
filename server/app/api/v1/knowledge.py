"""Knowledge base management API with upload and review workflow."""

import hashlib
import logging
import os
from collections import deque
from datetime import datetime, timezone
from urllib.parse import quote
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import ssl
import asyncio

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import select, func, delete as sql_delete, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db, get_session_factory
from app.core.exceptions import NotFoundError, BizError
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.models.knowledge import KnowledgeDocument, KnowledgeChunk, KnowledgeCrawlTask, KnowledgeBase
from app.models.audit_log import FileUploadLog
from app.schemas.knowledge import (
    KnowledgeDocResponse, KnowledgeDocListResponse,
    KnowledgeReviewRequest, ChunkPreviewResponse, ChunkListResponse, ChunkDetailResponse,
    ReembedRequest, ReembedResponse,
    CrawlTaskCreateRequest, CrawlTaskResponse, CrawlTaskListResponse,
)
from app.services.web_crawler_service import extract_page

logger = logging.getLogger(__name__)

router = APIRouter()


async def _ensure_crawl_task_table(db: AsyncSession) -> None:
    """Best-effort runtime schema guard to avoid 500 when migration was not applied."""
    await db.execute(sa_text(
        """
        CREATE TABLE IF NOT EXISTS knowledge_crawl_tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            kb_id UUID NOT NULL REFERENCES knowledge_bases(id),
            start_url VARCHAR(1000) NOT NULL,
            max_pages INTEGER NOT NULL DEFAULT 2,
            same_domain_only BOOLEAN NOT NULL DEFAULT true,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            progress INTEGER NOT NULL DEFAULT 0,
            total_pages INTEGER NOT NULL DEFAULT 0,
            success_pages INTEGER NOT NULL DEFAULT 0,
            failed_pages INTEGER NOT NULL DEFAULT 0,
            current_url VARCHAR(1000),
            error_message TEXT,
            result_document_ids JSONB,
            created_by UUID NOT NULL REFERENCES admin_users(id),
            started_at TIMESTAMPTZ,
            finished_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    ))
    await db.execute(sa_text(
        "CREATE INDEX IF NOT EXISTS ix_knowledge_crawl_tasks_kb_id ON knowledge_crawl_tasks(kb_id)"
    ))
    await db.execute(sa_text(
        "CREATE INDEX IF NOT EXISTS ix_knowledge_crawl_tasks_status ON knowledge_crawl_tasks(status)"
    ))
    await db.execute(sa_text(
        "CREATE INDEX IF NOT EXISTS ix_knowledge_crawl_tasks_created_at ON knowledge_crawl_tasks(created_at)"
    ))
    await db.commit()


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
        currentNode=doc.current_node or doc.status or "pending",
        uploaderId=str(doc.uploaded_by),
        uploaderName=uploader_name,
        reviewerId=str(doc.reviewed_by) if doc.reviewed_by else None,
        reviewerName=reviewer_name,
        reviewNote=doc.review_note,
        chunkCount=chunk_count,
        kbId=str(doc.kb_id) if doc.kb_id else None,
        createdAt=doc.created_at.isoformat(),
        updatedAt=doc.updated_at.isoformat(),
    )


async def _fetch_response_with_fallback(
    url: str,
    client: httpx.AsyncClient,
    insecure_client: httpx.AsyncClient,
) -> tuple[httpx.Response | None, str | None]:
    """Fetch URL with network fallbacks and return (response, error)."""
    try:
        return await client.get(url), None
    except Exception as err:
        first_err = str(err).strip() or repr(err)

    # TLS EOF fallback 1: insecure TLS
    if "TLS/SSL connection has been closed (EOF)" in first_err:
        try:
            return await insecure_client.get(url), f"TLS EOF 已触发降级重试(verify=false): {url}"
        except Exception as insecure_err:
            second_err = str(insecure_err).strip() or repr(insecure_err)
            # fallback 2: force plain http
            parsed = urlparse(url)
            if parsed.scheme == "https":
                http_url = f"http://{parsed.netloc}{parsed.path or '/'}"
                if parsed.query:
                    http_url += f"?{parsed.query}"
                try:
                    return await client.get(http_url), f"TLS EOF 已降级为HTTP抓取: {http_url}"
                except Exception:
                    pass
            # fallback 3: urllib stdlib with unverified ssl context
            try:
                def _urllib_fetch() -> tuple[int, dict[str, str], bytes]:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    req = Request(url, headers={"User-Agent": "BNU-KB-Crawler/1.0 (+https://admission.bnu.edu.cn)"})
                    with urlopen(req, context=ctx, timeout=20) as r:
                        headers = {k.lower(): v for k, v in r.headers.items()}
                        body = r.read()
                        return int(getattr(r, "status", 200)), headers, body

                status_code, headers, body = await asyncio.to_thread(_urllib_fetch)
                text = body.decode("utf-8", errors="ignore")
                response = httpx.Response(
                    status_code=status_code,
                    headers=headers,
                    text=text,
                    request=httpx.Request("GET", url),
                )
                return response, f"TLS EOF 已触发 urllib 降级抓取: {url}"
            except Exception as urllib_err:
                third_err = str(urllib_err).strip() or repr(urllib_err)
                return None, f"{url} -> TLS重试失败: {second_err}; urllib降级失败: {third_err}"

    return None, f"{url} -> {first_err}"


def _crawl_task_to_response(task: KnowledgeCrawlTask) -> CrawlTaskResponse:
    return CrawlTaskResponse(
        id=str(task.id),
        kbId=str(task.kb_id),
        startUrl=task.start_url,
        maxDepth=task.max_pages,
        sameDomainOnly=task.same_domain_only,
        status=task.status,
        progress=task.progress,
        totalPages=task.total_pages,
        successPages=task.success_pages,
        failedPages=task.failed_pages,
        currentUrl=task.current_url,
        errorMessage=task.error_message,
        resultDocumentIds=task.result_document_ids or [],
        createdBy=str(task.created_by),
        startedAt=task.started_at.isoformat() if task.started_at else None,
        finishedAt=task.finished_at.isoformat() if task.finished_at else None,
        createdAt=task.created_at.isoformat(),
        updatedAt=task.updated_at.isoformat(),
    )


@router.post("/upload", response_model=KnowledgeDocResponse,
             dependencies=[Depends(require_permission("knowledge:create"))])
async def upload_document(
    file: UploadFile = File(...),
    kb_id: str = Form(...),
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

    knowledge_dir = os.path.join(settings.UPLOAD_DIR, "knowledge")
    os.makedirs(knowledge_dir, exist_ok=True)
    file_path = os.path.join(knowledge_dir, f"{file_hash}.{ext}")
    with open(file_path, "wb") as f:
        f.write(content)

    doc = KnowledgeDocument(
        title=file.filename or "untitled",
        file_type=ext,
        file_path=file_path,
        file_hash=file_hash,
        status="pending",
        current_node="pending",
        uploaded_by=admin.id,
        kb_id=kb_id,
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
    kb_id: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100, alias="pageSize"),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """文档列表（分页筛选）"""
    stmt = select(KnowledgeDocument).where(KnowledgeDocument.status != "deleted")
    count_stmt = select(func.count()).select_from(KnowledgeDocument).where(KnowledgeDocument.status != "deleted")

    if status:
        stmt = stmt.where(KnowledgeDocument.current_node == status)
        count_stmt = count_stmt.where(KnowledgeDocument.current_node == status)

    if kb_id:
        stmt = stmt.where(KnowledgeDocument.kb_id == kb_id)
        count_stmt = count_stmt.where(KnowledgeDocument.kb_id == kb_id)

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


@router.post("/crawl/tasks", response_model=CrawlTaskResponse,
             dependencies=[Depends(require_permission("knowledge:create"))])
async def create_crawl_task(
    body: CrawlTaskCreateRequest,
    background_tasks: BackgroundTasks,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建网页爬取任务并在后台执行。"""
    await _ensure_crawl_task_table(db)

    kb = (await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == body.kbId))).scalar_one_or_none()
    if not kb:
        raise NotFoundError("知识库不存在")

    parsed = urlparse(str(body.startUrl))
    if parsed.scheme not in {"http", "https"}:
        raise BizError(code=400, message="startUrl 必须为 http/https 链接")

    task = KnowledgeCrawlTask(
        kb_id=body.kbId,
        start_url=str(body.startUrl),
        max_pages=body.maxDepth,
        same_domain_only=body.sameDomainOnly,
        status="pending",
        progress=0,
        created_by=admin.id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    background_tasks.add_task(_background_crawl_document, str(task.id))
    return _crawl_task_to_response(task)


@router.get("/crawl/tasks", response_model=CrawlTaskListResponse,
            dependencies=[Depends(require_permission("knowledge:read"))])
async def list_crawl_tasks(
    kb_id: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100, alias="pageSize"),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_crawl_task_table(db)

    stmt = select(KnowledgeCrawlTask)
    count_stmt = select(func.count()).select_from(KnowledgeCrawlTask)
    if kb_id:
        stmt = stmt.where(KnowledgeCrawlTask.kb_id == kb_id)
        count_stmt = count_stmt.where(KnowledgeCrawlTask.kb_id == kb_id)
    if status:
        stmt = stmt.where(KnowledgeCrawlTask.status == status)
        count_stmt = count_stmt.where(KnowledgeCrawlTask.status == status)

    total = (await db.execute(count_stmt)).scalar() or 0
    rows = (await db.execute(
        stmt.order_by(KnowledgeCrawlTask.created_at.desc()).offset((page - 1) * pageSize).limit(pageSize)
    )).scalars().all()
    return CrawlTaskListResponse(
        items=[_crawl_task_to_response(x) for x in rows],
        total=total,
        page=page,
        pageSize=pageSize,
    )


@router.get("/crawl/tasks/{task_id}", response_model=CrawlTaskResponse,
            dependencies=[Depends(require_permission("knowledge:read"))])
async def get_crawl_task(
    task_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_crawl_task_table(db)

    task = (await db.execute(select(KnowledgeCrawlTask).where(KnowledgeCrawlTask.id == task_id))).scalar_one_or_none()
    if not task:
        raise NotFoundError("爬取任务不存在")
    return _crawl_task_to_response(task)


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

    rows = (await db.execute(
        sa_text(
            """
            SELECT
                kc.id,
                kc.chunk_index,
                kc.content,
                kc.token_count,
                kc.embedding_model,
                CASE WHEN kc.embedding IS NULL THEN 'missing' ELSE 'generated' END AS embedding_status
            FROM knowledge_chunks kc
            WHERE kc.document_id = :doc_id
            ORDER BY kc.chunk_index
            OFFSET :offset
            LIMIT :limit
            """
        ),
        {
            "doc_id": str(doc_id),
            "offset": (page - 1) * pageSize,
            "limit": pageSize,
        },
    )).all()

    return ChunkListResponse(
        items=[
            ChunkPreviewResponse(
                id=str(row[0]),
                chunkIndex=row[1],
                content=row[2],
                tokenCount=row[3],
                embeddingModel=row[4],
                embeddingStatus=row[5],
            )
            for row in rows
        ],
        total=total, page=page, pageSize=pageSize,
    )


@router.get("/chunks/{chunk_id}/detail", response_model=ChunkDetailResponse,
            dependencies=[Depends(require_permission("knowledge:read"))])
async def get_chunk_detail(
    chunk_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取单个切片详情（含向量文本）。"""
    row = (await db.execute(
        sa_text(
            """
            SELECT
                kc.id,
                kc.chunk_index,
                kc.content,
                kc.token_count,
                kc.embedding_model,
                CASE WHEN kc.embedding IS NULL THEN 'missing' ELSE 'generated' END AS embedding_status,
                CASE WHEN kc.embedding IS NULL THEN NULL ELSE kc.embedding::text END AS embedding_vector
            FROM knowledge_chunks kc
            WHERE kc.id = :chunk_id
            LIMIT 1
            """
        ),
        {"chunk_id": chunk_id},
    )).first()

    if not row:
        raise NotFoundError("切片不存在")

    return ChunkDetailResponse(
        id=str(row[0]),
        chunkIndex=row[1],
        content=row[2],
        tokenCount=row[3],
        embeddingModel=row[4],
        embeddingStatus=row[5],
        embeddingVector=row[6],
    )


@router.post("/re-embed-missing", response_model=ReembedResponse,
             dependencies=[Depends(require_permission("knowledge:approve"))])
async def reembed_missing_chunks(
    body: ReembedRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """重跑缺失 embedding 的切片（全局或指定文档）。"""
    from app.services import model_config_service
    from app.services.knowledge_embedding_service import ensure_embedding_schema, backfill_missing_embeddings

    await model_config_service.reload_router(db)
    await ensure_embedding_schema(db)

    count_sql = "SELECT count(*) FROM knowledge_chunks WHERE embedding IS NULL"
    params: dict[str, str | int] = {}
    if body.documentId:
        await _get_document(body.documentId, db)
        count_sql += " AND document_id = :doc_id"
        params["doc_id"] = body.documentId

    missing_before = (await db.execute(sa_text(count_sql), params)).scalar() or 0

    if body.documentId:
        updated = await backfill_missing_embeddings(db, limit=body.limit, document_id=body.documentId)
    else:
        updated = await backfill_missing_embeddings(db, limit=body.limit)

    await db.commit()

    scope = f"文档 {body.documentId}" if body.documentId else "全库"
    return ReembedResponse(
        success=True,
        updated=updated,
        scanned=min(missing_before, body.limit),
        message=f"{scope} 缺失 embedding 重跑完成",
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

    current_node = doc.current_node or doc.status or "pending"

    # Use workflow service for state-machine action
    from app.services import review_workflow_service as wf_svc
    try:
        action_result = await wf_svc.execute_action(
            resource_type="knowledge",
            resource_id=doc.id,
            current_node=current_node,
            action=body.action,
            reviewer_id=admin.id,
            note=body.note,
            db=db,
        )
    except ValueError as e:
        raise BizError(code=400, message=str(e))

    doc.reviewed_by = admin.id
    doc.review_note = body.note
    doc.updated_at = datetime.now(timezone.utc)
    doc.current_node = action_result["new_node"]

    if action_result["new_node"] == "approved":
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
        doc.status = action_result["new_status"]
        await db.commit()
        await db.refresh(doc)

    return await _doc_to_response(doc, db)


async def _background_chunk_document(doc_id: str, file_path: str, file_type: str):
    """Background task: parse file, create chunks, update status."""
    session_factory = get_session_factory()
    async with session_factory() as db:
        try:
            from app.services.file_parser_service import parse_file, chunk_text
            from app.services.knowledge_embedding_service import ensure_embedding_schema, embed_document_chunks

            text = parse_file(file_path, file_type)
            text_chunks = chunk_text(text)

            # Ensure vector schema exists before writing embeddings (graceful no-op if unavailable)
            await ensure_embedding_schema(db)

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

            await db.flush()

            embedded_count = 0
            embedded_count = await embed_document_chunks(doc_id, db)
            if text_chunks and embedded_count < len(text_chunks):
                raise RuntimeError(
                    f"embedding generation incomplete: {embedded_count}/{len(text_chunks)}"
                )

            # Update document status to approved
            doc = (await db.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
            )).scalar_one()
            doc.status = "approved"
            doc.updated_at = datetime.now(timezone.utc)

            await db.commit()
            logger.info(
                "Document %s chunked: %d chunks, embedded: %d",
                doc_id,
                len(text_chunks),
                embedded_count,
            )

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


async def _background_crawl_document(task_id: str):
    """Background task: crawl pages and store page text as knowledge documents."""
    session_factory = get_session_factory()
    async with session_factory() as db:
        task = (await db.execute(select(KnowledgeCrawlTask).where(KnowledgeCrawlTask.id == task_id))).scalar_one_or_none()
        if not task:
            logger.error("crawl task not found: %s", task_id)
            return

        try:
            task.status = "running"
            task.started_at = datetime.now(timezone.utc)
            task.updated_at = datetime.now(timezone.utc)
            await db.commit()

            start_url = task.start_url
            root_host = urlparse(start_url).netloc
            max_depth = max(0, min(task.max_pages, 10))
            hard_page_cap = 500
            q: deque[tuple[str, int]] = deque([(start_url, 0)])
            visited: set[str] = set()
            created_doc_ids: list[str] = []
            processed = 0
            success = 0
            failed = 0
            last_error: str | None = None

            knowledge_dir = os.path.join(settings.UPLOAD_DIR, "knowledge")
            os.makedirs(knowledge_dir, exist_ok=True)

            headers = {"User-Agent": "BNU-KB-Crawler/1.0 (+https://admission.bnu.edu.cn)"}
            timeout = httpx.Timeout(connect=10.0, read=20.0, write=20.0, pool=10.0)
            async with (
                httpx.AsyncClient(
                    headers=headers,
                    timeout=timeout,
                    follow_redirects=True,
                    http2=False,
                    trust_env=False,
                ) as client,
                httpx.AsyncClient(
                    headers=headers,
                    timeout=timeout,
                    follow_redirects=True,
                    verify=False,
                    http2=False,
                    trust_env=False,
                ) as insecure_client,
            ):
                while q and len(visited) < hard_page_cap:
                    url, depth = q.popleft()
                    if url in visited:
                        continue
                    visited.add(url)
                    processed += 1

                    task.current_url = url
                    task.total_pages = processed
                    pending = len(q)
                    task.progress = min(99, int(processed * 100 / max(1, processed + pending)))
                    task.updated_at = datetime.now(timezone.utc)
                    await db.commit()

                    try:
                        resp, fetch_hint = await _fetch_response_with_fallback(url, client, insecure_client)
                        if resp is None:
                            last_error = (
                                f"{fetch_hint}（若持续失败，通常是运行容器出口网络/防火墙限制）"
                                if fetch_hint else
                                f"{url} -> 抓取失败（无响应）"
                            )
                            failed += 1
                            continue
                        if fetch_hint:
                            last_error = fetch_hint

                        resp.raise_for_status()
                        ctype = (resp.headers.get("content-type") or "").lower()
                        if "text/html" not in ctype and "application/xhtml+xml" not in ctype:
                            last_error = f"页面非HTML内容: {url}"
                            failed += 1
                            continue

                        title, body_text, links = extract_page(resp.text, str(resp.url))
                        body_text = body_text.strip()
                        if len(body_text) < 30:
                            last_error = f"页面正文过短或提取为空: {url}"
                            failed += 1
                            continue

                        file_hash = hashlib.sha256(body_text.encode("utf-8")).hexdigest()
                        file_path = os.path.join(knowledge_dir, f"{file_hash}.txt")
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(body_text)

                        # Keep title as source URL so admin can directly identify crawl origin.
                        doc_title = str(resp.url)
                        doc = KnowledgeDocument(
                            title=doc_title[:300],
                            file_type="txt",
                            file_path=file_path,
                            file_hash=file_hash,
                            status="pending",
                            current_node="pending",
                            uploaded_by=task.created_by,
                            kb_id=task.kb_id,
                        )
                        db.add(doc)
                        await db.flush()
                        created_doc_ids.append(str(doc.id))
                        success += 1

                        if depth < max_depth:
                            for link in links:
                                if link in visited:
                                    continue
                                if task.same_domain_only and urlparse(link).netloc != root_host:
                                    continue
                                if len(visited) + len(q) >= hard_page_cap:
                                    break
                                q.append((link, depth + 1))
                    except Exception as crawl_err:
                        logger.warning("crawl failed for task=%s url=%s error=%s", task_id, url, crawl_err)
                        detail = str(crawl_err).strip() or repr(crawl_err)
                        last_error = f"{url} -> {detail}"
                        failed += 1

                    task.success_pages = success
                    task.failed_pages = failed
                    task.total_pages = processed
                    task.result_document_ids = created_doc_ids
                    task.error_message = last_error
                    task.updated_at = datetime.now(timezone.utc)
                    await db.commit()

            if success == 0 and failed > 0:
                task.status = "failed"
                task.error_message = last_error or "未抓取到可用页面内容"
            else:
                task.status = "success"
            task.progress = 100
            task.total_pages = processed
            task.success_pages = success
            task.failed_pages = failed
            task.result_document_ids = created_doc_ids
            task.current_url = None
            task.finished_at = datetime.now(timezone.utc)
            task.updated_at = datetime.now(timezone.utc)
            await db.commit()
        except Exception as e:
            logger.error("Failed to crawl document for task %s: %s", task_id, e)
            task.status = "failed"
            task.error_message = str(e).strip() or repr(e)
            task.finished_at = datetime.now(timezone.utc)
            task.updated_at = datetime.now(timezone.utc)
            await db.commit()


from pydantic import BaseModel as _PydanticBaseModel


class BatchReviewRequest(_PydanticBaseModel):
    ids: list[str]
    action: str
    note: str | None = None


class BatchDeleteRequest(_PydanticBaseModel):
    ids: list[str]


@router.post("/batch-review", dependencies=[Depends(require_permission("knowledge:approve"))])
async def batch_review_documents(
    body: BatchReviewRequest,
    background_tasks: BackgroundTasks,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """批量审核知识文档"""
    from app.services import review_workflow_service as wf_svc

    success_count = 0
    errors: list[str] = []

    for doc_id in body.ids:
        result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            errors.append(f"{doc_id}: 文档不存在")
            continue

        current_node = doc.current_node or doc.status or "pending"
        try:
            action_result = await wf_svc.execute_action(
                resource_type="knowledge",
                resource_id=doc.id,
                current_node=current_node,
                action=body.action,
                reviewer_id=admin.id,
                note=body.note,
                db=db,
            )
            doc.reviewed_by = admin.id
            doc.review_note = body.note
            doc.updated_at = datetime.now(timezone.utc)
            doc.current_node = action_result["new_node"]

            if action_result["new_node"] == "approved":
                doc.status = "processing"
                doc.effective_from = datetime.now(timezone.utc)
                background_tasks.add_task(
                    _background_chunk_document,
                    str(doc.id), doc.file_path, doc.file_type,
                )
            else:
                doc.status = action_result["new_status"]

            success_count += 1
        except ValueError as e:
            errors.append(f"{doc.title}: {str(e)}")

    await db.commit()
    return {"success": True, "success_count": success_count, "errors": errors}


@router.post("/batch-delete", dependencies=[Depends(require_permission("knowledge:delete"))])
async def batch_delete_documents(
    body: BatchDeleteRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """批量软删除知识文档"""
    success_count = 0
    errors: list[str] = []

    for doc_id in body.ids:
        result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            errors.append(f"{doc_id}: 文档不存在")
            continue
        if doc.status == "deleted":
            continue

        doc.status = "deleted"
        doc.current_node = "deleted"
        doc.updated_at = datetime.now(timezone.utc)
        success_count += 1

    await db.commit()
    return {"success": True, "success_count": success_count, "errors": errors}


@router.delete("/{doc_id}", dependencies=[Depends(require_permission("knowledge:delete"))])
async def soft_delete_document(
    doc_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """软删除文档"""
    doc = await _get_document(doc_id, db)
    doc.status = "deleted"
    doc.current_node = "deleted"
    doc.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True, "message": "文档已删除"}


async def _get_document(doc_id: str, db: AsyncSession) -> KnowledgeDocument:
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("文档不存在")
    return doc
