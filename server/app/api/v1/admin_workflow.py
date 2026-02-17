"""Admin API endpoints for workflow management."""

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
    definition: dict


class WorkflowUpdateRequest(BaseModel):
    name: str | None = None
    definition: dict | None = None


class BindingUpdateRequest(BaseModel):
    workflow_id: str | None = None
    enabled: bool | None = None


@router.get("/workflows", dependencies=[Depends(require_permission("role:read"))])
async def list_workflows(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """列出所有工作流模板"""
    workflows = await wf_svc.list_workflows(db)
    return {"items": workflows}


@router.post("/workflows", dependencies=[Depends(require_permission("role:update"))])
async def create_workflow(
    body: WorkflowCreateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建工作流模板"""
    if not body.definition or not body.definition.get("nodes"):
        raise BizError(code=400, message="工作流定义不能为空")
    try:
        result = await wf_svc.create_workflow(body.name, body.code, body.definition, db)
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
    """更新工作流模板"""
    try:
        result = await wf_svc.update_workflow(workflow_id, body.name, body.definition, db)
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
    """删除工作流模板"""
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
    """列出资源类型的工作流绑定"""
    bindings = await wf_svc.list_bindings(db)
    return {"items": bindings}


@router.put("/workflows/bindings/{resource_type}", dependencies=[Depends(require_permission("role:update"))])
async def update_binding(
    resource_type: str,
    body: BindingUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新资源类型的工作流绑定"""
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


@router.get("/workflows/for-resource/{resource_type}", dependencies=[Depends(require_permission("role:read"))])
async def get_workflow_for_resource(
    resource_type: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取资源类型的工作流定义（供前端渲染节点标签和动作按钮）"""
    defn = await wf_svc.get_workflow_definition_for_resource(resource_type, db)
    if not defn:
        return {"workflow_id": None, "nodes": [], "actions": [], "transitions": []}
    return defn


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
