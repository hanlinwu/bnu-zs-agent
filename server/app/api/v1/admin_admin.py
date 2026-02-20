"""Admin user management API for super administrators."""

from datetime import datetime, timezone
import re

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_
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
    employee_id: str | None = None
    department: str | None = None
    title: str | None = None
    phone: str
    email: str | None = None
    avatar_url: str | None = None
    role_code: str | None = None


class AdminUpdateRequest(BaseModel):
    real_name: str | None = None
    employee_id: str | None = None
    department: str | None = None
    title: str | None = None
    phone: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    role_code: str | None = None
    status: str | None = None


def _normalize_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized if normalized else None


def _is_valid_phone(phone: str | None) -> bool:
    if not phone:
        return False
    return re.fullmatch(r"^1[3-9]\d{9}$", phone) is not None


def _is_strong_password(password: str) -> bool:
    if len(password) < 8:
        return False
    has_upper = re.search(r"[A-Z]", password) is not None
    has_lower = re.search(r"[a-z]", password) is not None
    has_digit = re.search(r"\d", password) is not None
    has_special = re.search(r"[^A-Za-z0-9]", password) is not None
    return has_upper and has_lower and has_digit and has_special


async def _get_role_map_for_admin_ids(admin_ids: list, db: AsyncSession) -> dict[str, dict[str, str | None]]:
    if not admin_ids:
        return {}
    role_stmt = (
        select(AdminRole.admin_id, Role.code, Role.name)
        .join(Role, Role.id == AdminRole.role_id)
        .where(AdminRole.admin_id.in_(admin_ids))
    )
    role_rows = (await db.execute(role_stmt)).all()
    role_map: dict[str, dict[str, str | None]] = {}
    for admin_id, role_code, role_name in role_rows:
        role_map[str(admin_id)] = {
            "role_code": role_code,
            "role_name": role_name,
        }
    return role_map


def _admin_to_dict(
    item: AdminUser,
    role_code: str | None = None,
    role_name: str | None = None,
    created_by_name: str | None = None,
) -> dict:
    return {
        "id": str(item.id),
        "username": item.username,
        "real_name": item.real_name,
        "nickname": item.real_name,
        "employee_id": item.employee_id,
        "department": item.department,
        "title": item.title,
        "phone": item.phone or "",
        "email": item.email,
        "avatar_url": item.avatar_url or "",
        "status": item.status,
        "role_code": role_code,
        "role_name": role_name,
        "last_login_at": item.last_login_at.isoformat() if item.last_login_at else None,
        "last_login_ip": str(item.last_login_ip) if item.last_login_ip else None,
        "token_expire_at": item.token_expire_at.isoformat() if item.token_expire_at else None,
        "created_by": str(item.created_by) if item.created_by else None,
        "created_by_name": created_by_name,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }


async def _get_admin_display_name_map(admin_ids: list, db: AsyncSession) -> dict[str, str]:
    if not admin_ids:
        return {}
    stmt = select(AdminUser.id, AdminUser.real_name, AdminUser.username).where(AdminUser.id.in_(admin_ids))
    rows = (await db.execute(stmt)).all()
    result: dict[str, str] = {}
    for admin_id, real_name, username in rows:
        result[str(admin_id)] = real_name or username
    return result


@router.get("", dependencies=[Depends(require_permission("admin:read"))])
async def list_admins(
    keyword: str | None = None,
    status: str | None = None,
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
            or_(
                AdminUser.username.ilike(like_pattern),
                AdminUser.real_name.ilike(like_pattern),
                AdminUser.employee_id.ilike(like_pattern),
                AdminUser.department.ilike(like_pattern),
                AdminUser.title.ilike(like_pattern),
                AdminUser.phone.ilike(like_pattern),
                AdminUser.email.ilike(like_pattern),
            )
        )
        count_stmt = count_stmt.where(
            or_(
                AdminUser.username.ilike(like_pattern),
                AdminUser.real_name.ilike(like_pattern),
                AdminUser.employee_id.ilike(like_pattern),
                AdminUser.department.ilike(like_pattern),
                AdminUser.title.ilike(like_pattern),
                AdminUser.phone.ilike(like_pattern),
                AdminUser.email.ilike(like_pattern),
            )
        )

    if status:
        stmt = stmt.where(AdminUser.status == status)
        count_stmt = count_stmt.where(AdminUser.status == status)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = (
        stmt.order_by(AdminUser.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    admins = result.scalars().all()

    role_map = await _get_role_map_for_admin_ids([a.id for a in admins], db)
    creator_name_map = await _get_admin_display_name_map(
        [a.created_by for a in admins if a.created_by is not None], db
    )
    items = []
    for item in admins:
        role_info = role_map.get(str(item.id), {})
        creator_name = creator_name_map.get(str(item.created_by)) if item.created_by else None
        items.append(_admin_to_dict(item, role_info.get("role_code"), role_info.get("role_name"), creator_name))

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
    if not _is_strong_password(body.password):
        raise BizError(code=400, message="密码需包含大小写字母、数字和特殊字符")

    phone = _normalize_optional_str(body.phone)
    if not _is_valid_phone(phone):
        raise BizError(code=400, message="手机号格式不正确")

    employee_id = _normalize_optional_str(body.employee_id)
    if employee_id:
        exists_employee_id = await db.execute(select(AdminUser).where(AdminUser.employee_id == employee_id))
        if exists_employee_id.scalar_one_or_none():
            raise BizError(code=400, message=f"工号 '{employee_id}' 已存在")

    new_admin = AdminUser(
        username=body.username,
        password_hash=hash_password(body.password),
        real_name=body.real_name,
        employee_id=employee_id,
        department=_normalize_optional_str(body.department),
        title=_normalize_optional_str(body.title),
        phone=phone,
        email=_normalize_optional_str(body.email),
        avatar_url=_normalize_optional_str(body.avatar_url) or "",
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

    role_name = None
    if body.role_code:
        role_result = await db.execute(select(Role.name).where(Role.code == body.role_code))
        role_name = role_result.scalar_one_or_none()
    creator_name = admin.real_name or admin.username
    return _admin_to_dict(new_admin, body.role_code, role_name, creator_name)


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
    if body.employee_id is not None:
        employee_id = _normalize_optional_str(body.employee_id)
        if employee_id:
            exists_employee_id = await db.execute(
                select(AdminUser).where(
                    AdminUser.employee_id == employee_id,
                    AdminUser.id != target.id,
                )
            )
            if exists_employee_id.scalar_one_or_none():
                raise BizError(code=400, message=f"工号 '{employee_id}' 已存在")
        target.employee_id = employee_id
    if body.department is not None:
        target.department = _normalize_optional_str(body.department)
    if body.title is not None:
        target.title = _normalize_optional_str(body.title)
    if body.phone is not None:
        phone = _normalize_optional_str(body.phone)
        if not _is_valid_phone(phone):
            raise BizError(code=400, message="手机号格式不正确")
        target.phone = phone
    if body.email is not None:
        target.email = _normalize_optional_str(body.email)
    if body.avatar_url is not None:
        target.avatar_url = _normalize_optional_str(body.avatar_url) or ""
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


class BatchStatusRequest(BaseModel):
    ids: list[str]
    status: str  # "active" or "disabled"


class BatchDeleteRequest(BaseModel):
    ids: list[str]


@router.put("/batch-status", dependencies=[Depends(require_permission("admin:update"))])
async def batch_update_admin_status(
    body: BatchStatusRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """批量启用/禁用管理员"""
    if body.status not in ("active", "disabled"):
        raise BizError(code=400, message="status 必须为 active 或 disabled")

    success_count = 0
    errors: list[str] = []

    for admin_id in body.ids:
        if str(admin.id) == admin_id:
            errors.append(f"{admin_id}: 不能修改自己的状态")
            continue
        result = await db.execute(select(AdminUser).where(AdminUser.id == admin_id))
        target = result.scalar_one_or_none()
        if not target:
            errors.append(f"{admin_id}: 管理员不存在")
            continue
        target.status = body.status
        target.updated_at = datetime.now(timezone.utc)
        success_count += 1

    await db.commit()
    label = "启用" if body.status == "active" else "禁用"
    return {"success": True, "success_count": success_count, "message": f"批量{label}完成", "errors": errors}


@router.post("/batch-delete", dependencies=[Depends(require_permission("admin:delete"))])
async def batch_delete_admins(
    body: BatchDeleteRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """批量删除管理员"""
    from sqlalchemy import delete

    success_count = 0
    errors: list[str] = []

    for admin_id in body.ids:
        if str(admin.id) == admin_id:
            errors.append(f"{admin_id}: 不能删除自己的账号")
            continue
        result = await db.execute(select(AdminUser).where(AdminUser.id == admin_id))
        target = result.scalar_one_or_none()
        if not target:
            errors.append(f"{admin_id}: 管理员不存在")
            continue
        await db.execute(delete(AdminRole).where(AdminRole.admin_id == target.id))
        await db.delete(target)
        success_count += 1

    await db.commit()
    return {"success": True, "success_count": success_count, "message": "批量删除完成", "errors": errors}


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
