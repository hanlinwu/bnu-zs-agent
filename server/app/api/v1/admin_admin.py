"""Admin user management API for super administrators."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError, BizError
from app.core.permissions import require_permission
from app.core.security import hash_password
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.models.role import Role, AdminRole

router = APIRouter()


class AdminCreateRequest(BaseModel):
    username: str
    password: str
    real_name: str
    phone: str | None = None
    role_code: str | None = None


class AdminUpdateRequest(BaseModel):
    real_name: str | None = None
    phone: str | None = None
    role_code: str | None = None
    status: str | None = None


@router.get("", dependencies=[Depends(require_permission("admin:read"))])
async def list_admins(
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理员列表（分页）"""
    stmt = select(AdminUser)
    count_stmt = select(func.count()).select_from(AdminUser)

    if keyword:
        like_pattern = f"%{keyword}%"
        stmt = stmt.where(
            (AdminUser.username.ilike(like_pattern))
            | (AdminUser.real_name.ilike(like_pattern))
            | (AdminUser.phone.like(like_pattern))
        )
        count_stmt = count_stmt.where(
            (AdminUser.username.ilike(like_pattern))
            | (AdminUser.real_name.ilike(like_pattern))
            | (AdminUser.phone.like(like_pattern))
        )

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = (
        stmt.order_by(AdminUser.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    admins = result.scalars().all()

    items = []
    for a in admins:
        # Fetch assigned role
        role_stmt = (
            select(Role.code, Role.name)
            .join(AdminRole, AdminRole.role_id == Role.id)
            .where(AdminRole.admin_id == a.id)
        )
        role_result = await db.execute(role_stmt)
        role_row = role_result.first()

        items.append({
            "id": str(a.id),
            "username": a.username,
            "real_name": a.real_name,
            "nickname": a.real_name,
            "phone": a.phone or "",
            "status": a.status,
            "role_code": role_row[0] if role_row else None,
            "role_name": role_row[1] if role_row else None,
            "last_login_at": a.last_login_at.isoformat() if a.last_login_at else None,
            "created_at": a.created_at.isoformat(),
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("", dependencies=[Depends(require_permission("admin:create"))])
async def create_admin(
    body: AdminCreateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建管理员"""
    existing = await db.execute(select(AdminUser).where(AdminUser.username == body.username))
    if existing.scalar_one_or_none():
        raise BizError(code=400, message=f"用户名 '{body.username}' 已存在")

    if len(body.password) < 8:
        raise BizError(code=400, message="密码至少8位")

    new_admin = AdminUser(
        username=body.username,
        password_hash=hash_password(body.password),
        real_name=body.real_name,
        phone=body.phone,
        status="active",
        created_by=admin.id,
    )
    db.add(new_admin)
    await db.flush()

    # Assign role if specified
    if body.role_code:
        role_result = await db.execute(select(Role).where(Role.code == body.role_code))
        role = role_result.scalar_one_or_none()
        if role:
            db.add(AdminRole(admin_id=new_admin.id, role_id=role.id))

    await db.commit()
    await db.refresh(new_admin)

    return {
        "id": str(new_admin.id),
        "username": new_admin.username,
        "real_name": new_admin.real_name,
        "status": new_admin.status,
    }


@router.put("/{admin_id}", dependencies=[Depends(require_permission("admin:update"))])
async def update_admin(
    admin_id: str,
    body: AdminUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """编辑管理员"""
    result = await db.execute(select(AdminUser).where(AdminUser.id == admin_id))
    target = result.scalar_one_or_none()
    if not target:
        raise NotFoundError("管理员不存在")

    if body.real_name is not None:
        target.real_name = body.real_name
    if body.phone is not None:
        target.phone = body.phone
    if body.status is not None:
        target.status = body.status

    if body.role_code is not None:
        # Replace role assignment
        from sqlalchemy import delete
        await db.execute(delete(AdminRole).where(AdminRole.admin_id == target.id))
        role_result = await db.execute(select(Role).where(Role.code == body.role_code))
        role = role_result.scalar_one_or_none()
        if role:
            db.add(AdminRole(admin_id=target.id, role_id=role.id))

    target.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"success": True, "message": "管理员信息已更新"}


@router.delete("/{admin_id}", dependencies=[Depends(require_permission("admin:delete"))])
async def delete_admin(
    admin_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除管理员"""
    if str(admin.id) == admin_id:
        raise BizError(code=400, message="不能删除自己的账号")

    result = await db.execute(select(AdminUser).where(AdminUser.id == admin_id))
    target = result.scalar_one_or_none()
    if not target:
        raise NotFoundError("管理员不存在")

    from sqlalchemy import delete
    await db.execute(delete(AdminRole).where(AdminRole.admin_id == target.id))
    await db.delete(target)
    await db.commit()

    return {"success": True, "message": "管理员已删除"}
