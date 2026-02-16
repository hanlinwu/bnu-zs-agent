"""Admin API endpoints for review workflow management."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BizError
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.services import review_workflow_service as wf_svc

router = APIRouter()


class WorkflowCreateRequest(BaseModel):
    name: str
    code: str
    steps: list[dict]


class WorkflowUpdateRequest(BaseModel):
    name: str | None = None
    steps: list[dict] | None = None


class BindingUpdateRequest(BaseModel):
    workflow_id: str | None = None
    enabled: bool | None = None


@router.get("/workflows", dependencies=[Depends(require_permission("role:read"))])
async def list_workflows(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """列出所有审核流程模板"""
    workflows = await wf_svc.list_workflows(db)
    return {"items": workflows}


@router.post("/workflows", dependencies=[Depends(require_permission("role:update"))])
async def create_workflow(
    body: WorkflowCreateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建审核流程模板"""
    if not body.steps:
        raise BizError(code=400, message="审核步骤不能为空")
    try:
        result = await wf_svc.create_workflow(body.name, body.code, body.steps, db)
        await db.commit()
        return result
    except Exception as e:
        await db.rollback()
        raise BizError(code=400, message=str(e))


@router.put("/workflows/{workflow_id}", dependencies=[Depends(require_permission("role:update"))])
async def update_workflow(
    workflow_id: str,
    body: WorkflowUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新审核流程模板"""
    try:
        result = await wf_svc.update_workflow(workflow_id, body.name, body.steps, db)
        await db.commit()
        return result
    except ValueError as e:
        raise BizError(code=400, message=str(e))


@router.delete("/workflows/{workflow_id}", dependencies=[Depends(require_permission("role:update"))])
async def delete_workflow(
    workflow_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除审核流程模板"""
    try:
        await wf_svc.delete_workflow(workflow_id, db)
        await db.commit()
        return {"success": True, "message": "已删除"}
    except ValueError as e:
        raise BizError(code=400, message=str(e))


@router.get("/workflows/bindings", dependencies=[Depends(require_permission("role:read"))])
async def list_bindings(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """列出资源类型的审核流程绑定"""
    bindings = await wf_svc.list_bindings(db)
    return {"items": bindings}


@router.put("/workflows/bindings/{resource_type}", dependencies=[Depends(require_permission("role:update"))])
async def update_binding(
    resource_type: str,
    body: BindingUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新资源类型的审核流程绑定"""
    try:
        result = await wf_svc.update_binding(
            resource_type,
            body.workflow_id if body.workflow_id else None,
            body.enabled,
            db,
        )
        await db.commit()
        return result
    except ValueError as e:
        raise BizError(code=400, message=str(e))


@router.get("/workflows/history/{resource_type}/{resource_id}", dependencies=[Depends(require_permission("role:read"))])
async def get_review_history(
    resource_type: str,
    resource_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取资源的审核历史"""
    records = await wf_svc.get_review_history(resource_type, resource_id, db)
    return {"items": records}
