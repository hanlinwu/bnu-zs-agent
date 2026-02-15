"""Role & permission management API for administrators."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError, BizError
from app.core.permissions import require_permission, invalidate_admin_permissions
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.models.role import Role, Permission, RolePermission, AdminRole

router = APIRouter()


class RoleCreateRequest(BaseModel):
    code: str
    name: str
    role_type: str = "admin"
    description: str | None = None


class RoleUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class AssignPermissionsRequest(BaseModel):
    permission_ids: list[str]


@router.get("/roles", dependencies=[Depends(require_permission("role:read"))])
async def list_roles(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """角色列表"""
    result = await db.execute(select(Role).order_by(Role.created_at))
    roles = result.scalars().all()

    items = []
    for r in roles:
        # Fetch permission count for each role
        perm_stmt = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == r.id)
        )
        perm_result = await db.execute(perm_stmt)
        perm_codes = [row[0] for row in perm_result.all()]

        items.append({
            "id": str(r.id),
            "code": r.code,
            "name": r.name,
            "role_type": r.role_type,
            "description": r.description,
            "is_system": r.is_system,
            "permissions": perm_codes,
            "created_at": r.created_at.isoformat(),
        })

    return {"items": items}


@router.post("/roles", dependencies=[Depends(require_permission("role:create"))])
async def create_role(
    body: RoleCreateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建角色"""
    # Check code uniqueness
    existing = await db.execute(select(Role).where(Role.code == body.code))
    if existing.scalar_one_or_none():
        raise BizError(code=400, message=f"角色编码 '{body.code}' 已存在")

    role = Role(
        code=body.code,
        name=body.name,
        role_type=body.role_type,
        description=body.description,
        is_system=False,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)

    return {
        "id": str(role.id),
        "code": role.code,
        "name": role.name,
        "role_type": role.role_type,
        "description": role.description,
        "is_system": role.is_system,
        "created_at": role.created_at.isoformat(),
    }


@router.put("/roles/{role_id}", dependencies=[Depends(require_permission("role:update"))])
async def update_role(
    role_id: str,
    body: RoleUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """编辑角色"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise NotFoundError("角色不存在")

    if role.is_system:
        raise BizError(code=400, message="系统内置角色不可编辑")

    if body.name is not None:
        role.name = body.name
    if body.description is not None:
        role.description = body.description

    await db.commit()
    await db.refresh(role)

    return {
        "id": str(role.id),
        "code": role.code,
        "name": role.name,
        "description": role.description,
    }


@router.put("/roles/{role_id}/permissions", dependencies=[Depends(require_permission("role:update"))])
async def assign_permissions(
    role_id: str,
    body: AssignPermissionsRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """为角色分配权限（全量替换）"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise NotFoundError("角色不存在")

    # Validate all permission_ids exist
    for pid in body.permission_ids:
        perm = await db.execute(select(Permission).where(Permission.id == pid))
        if not perm.scalar_one_or_none():
            raise NotFoundError(f"权限 {pid} 不存在")

    # Remove existing bindings
    await db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))

    # Add new bindings
    for pid in body.permission_ids:
        db.add(RolePermission(role_id=role.id, permission_id=pid))

    await db.commit()

    # Invalidate cached permissions for all admins with this role
    admin_roles_result = await db.execute(
        select(AdminRole.admin_id).where(AdminRole.role_id == role.id)
    )
    for row in admin_roles_result.all():
        await invalidate_admin_permissions(str(row[0]))

    return {"success": True, "message": "权限已更新"}


@router.get("/permissions", dependencies=[Depends(require_permission("role:read"))])
async def list_permissions(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """权限列表"""
    result = await db.execute(select(Permission).order_by(Permission.resource, Permission.action))
    permissions = result.scalars().all()

    return {
        "items": [
            {
                "id": str(p.id),
                "code": p.code,
                "name": p.name,
                "resource": p.resource,
                "action": p.action,
                "description": p.description,
            }
            for p in permissions
        ]
    }
