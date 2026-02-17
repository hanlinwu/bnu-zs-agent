"""Knowledge base (库) CRUD API."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError, BizError
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.models.knowledge import KnowledgeBase, KnowledgeDocument

router = APIRouter()


class KBCreateRequest(BaseModel):
    name: str
    description: str | None = None
    enabled: bool = True
    sort_order: int = 0


class KBUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    sort_order: int | None = None


@router.get("", dependencies=[Depends(require_permission("knowledge:read"))])
async def list_knowledge_bases(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """知识库列表（含文档数量统计）"""
    stmt = (
        select(KnowledgeBase)
        .order_by(KnowledgeBase.sort_order, KnowledgeBase.created_at)
    )
    result = await db.execute(stmt)
    kbs = result.scalars().all()

    items = []
    for kb in kbs:
        doc_count = (await db.execute(
            select(func.count()).select_from(KnowledgeDocument)
            .where(KnowledgeDocument.kb_id == kb.id)
        )).scalar() or 0
        items.append({
            "id": str(kb.id),
            "name": kb.name,
            "description": kb.description or "",
            "enabled": kb.enabled,
            "sort_order": kb.sort_order,
            "doc_count": doc_count,
            "created_at": kb.created_at.isoformat(),
            "updated_at": kb.updated_at.isoformat(),
        })

    return {"items": items}


@router.post("", dependencies=[Depends(require_permission("knowledge:create"))])
async def create_knowledge_base(
    body: KBCreateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建知识库"""
    kb = KnowledgeBase(
        name=body.name,
        description=body.description,
        enabled=body.enabled,
        sort_order=body.sort_order,
        created_by=admin.id,
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return {
        "id": str(kb.id),
        "name": kb.name,
        "description": kb.description or "",
        "enabled": kb.enabled,
        "sort_order": kb.sort_order,
        "created_at": kb.created_at.isoformat(),
    }


@router.put("/{kb_id}", dependencies=[Depends(require_permission("knowledge:create"))])
async def update_knowledge_base(
    kb_id: str,
    body: KBUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """编辑知识库"""
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()
    if not kb:
        raise NotFoundError("知识库不存在")

    if body.name is not None:
        kb.name = body.name
    if body.description is not None:
        kb.description = body.description
    if body.enabled is not None:
        kb.enabled = body.enabled
    if body.sort_order is not None:
        kb.sort_order = body.sort_order
    kb.updated_at = datetime.now(timezone.utc)

    await db.commit()
    return {"success": True, "message": "知识库已更新"}


@router.delete("/{kb_id}", dependencies=[Depends(require_permission("knowledge:delete"))])
async def delete_knowledge_base(
    kb_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除知识库（仅允许删除空库）"""
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()
    if not kb:
        raise NotFoundError("知识库不存在")

    doc_count = (await db.execute(
        select(func.count()).select_from(KnowledgeDocument)
        .where(KnowledgeDocument.kb_id == kb.id)
    )).scalar() or 0

    if doc_count > 0:
        raise BizError(code=400, message=f"该知识库下还有 {doc_count} 篇文档，请先移除或删除文档")

    await db.delete(kb)
    await db.commit()
    return {"success": True, "message": "知识库已删除"}
