"""Global dependencies for FastAPI dependency injection."""

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import verify_token
from app.models.user import User
from app.models.admin import AdminUser


async def get_current_user(
    authorization: str = Header(..., description="Bearer token"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate current user from JWT token."""
    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("无效的认证头")

    token = authorization[7:]
    try:
        payload = verify_token(token)
    except Exception:
        raise UnauthorizedError("Token 无效或已过期")

    if payload.get("type") != "user":
        raise UnauthorizedError("Token 类型错误")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Token 无效")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedError("用户不存在")
    if user.status != "active":
        raise UnauthorizedError("账号已被禁用")

    return user


async def get_current_admin(
    authorization: str = Header(..., description="Bearer token"),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    """Extract and validate current admin from JWT token."""
    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("无效的认证头")

    token = authorization[7:]
    try:
        payload = verify_token(token)
    except Exception:
        raise UnauthorizedError("Token 无效或已过期")

    if payload.get("type") != "admin":
        raise UnauthorizedError("需要管理员权限")

    admin_id = payload.get("sub")
    if not admin_id:
        raise UnauthorizedError("Token 无效")

    result = await db.execute(select(AdminUser).where(AdminUser.id == admin_id))
    admin = result.scalar_one_or_none()

    if not admin:
        raise UnauthorizedError("管理员不存在")
    if admin.status != "active":
        raise UnauthorizedError("管理员账号已被禁用")

    return admin
