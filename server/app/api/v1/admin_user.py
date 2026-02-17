"""User management API for administrators."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError, BizError
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.models.user import User

router = APIRouter()


@router.get("", dependencies=[Depends(require_permission("user:read"))])
async def list_users(
    status: str | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """用户列表（分页、按状态筛选）"""
    stmt = select(User)
    count_stmt = select(func.count()).select_from(User)

    if status:
        stmt = stmt.where(User.status == status)
        count_stmt = count_stmt.where(User.status == status)

    if keyword:
        like_pattern = f"%{keyword}%"
        stmt = stmt.where(
            (User.nickname.ilike(like_pattern)) | (User.phone.like(like_pattern))
        )
        count_stmt = count_stmt.where(
            (User.nickname.ilike(like_pattern)) | (User.phone.like(like_pattern))
        )

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = (
        stmt.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    users = result.scalars().all()

    return {
        "items": [
            {
                "id": str(u.id),
                "phone": u.phone,
                "nickname": u.nickname,
                "avatar_url": u.avatar_url,
                "gender": u.gender,
                "province": u.province,
                "school": u.school,
                "status": u.status,
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


from pydantic import BaseModel


class BatchBanRequest(BaseModel):
    ids: list[str]
    action: str  # "ban" or "unban"


@router.put("/batch-ban", dependencies=[Depends(require_permission("user:ban"))])
async def batch_ban_users(
    body: BatchBanRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """批量封禁/解封用户"""
    if body.action not in ("ban", "unban"):
        raise BizError(code=400, message="action 必须为 ban 或 unban")

    target_status = "banned" if body.action == "ban" else "active"
    success_count = 0
    errors: list[str] = []

    for user_id in body.ids:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            errors.append(f"{user_id}: 用户不存在")
            continue
        user.status = target_status
        user.updated_at = datetime.now(timezone.utc)
        success_count += 1

    await db.commit()
    label = "封禁" if body.action == "ban" else "解封"
    return {"success": True, "success_count": success_count, "message": f"批量{label}完成", "errors": errors}


@router.put("/{user_id}/ban", dependencies=[Depends(require_permission("user:ban"))])
async def toggle_ban_user(
    user_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """封禁/解封用户"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("用户不存在")

    if user.status == "active":
        user.status = "banned"
        message = "用户已封禁"
    elif user.status == "banned":
        user.status = "active"
        message = "用户已解封"
    else:
        raise BizError(code=400, message=f"当前状态 '{user.status}' 不支持此操作")

    user.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"success": True, "message": message, "status": user.status}
