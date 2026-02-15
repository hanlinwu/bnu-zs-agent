"""RBAC permission checking decorator with Redis caching."""

from functools import wraps
from typing import Callable

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError
from app.core.redis import redis_client
from app.models.admin import AdminUser
from app.models.role import AdminRole, RolePermission, Permission


CACHE_TTL = 300  # 5 minutes


async def get_admin_permissions(admin_id: str, db: AsyncSession) -> set[str]:
    """Get all permission codes for an admin, with Redis caching."""
    cache_key = f"admin_perms:{admin_id}"

    # Try Redis cache first
    try:
        cached = await redis_client.smembers(cache_key)
        if cached:
            return cached
    except Exception:
        pass

    # Query DB: admin_roles → role_permissions → permissions
    stmt = (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(AdminRole, AdminRole.role_id == RolePermission.role_id)
        .where(AdminRole.admin_id == admin_id)
    )
    result = await db.execute(stmt)
    permissions = {row[0] for row in result.all()}

    # Cache in Redis
    if permissions:
        try:
            await redis_client.sadd(cache_key, *permissions)
            await redis_client.expire(cache_key, CACHE_TTL)
        except Exception:
            pass

    return permissions


def require_permission(*permission_codes: str):
    """RBAC permission checking dependency factory.

    Usage:
        @router.post("/", dependencies=[Depends(require_permission("knowledge:create"))])
        async def create_doc(admin: AdminUser = Depends(get_current_admin)):
            ...
    """
    async def _check_permission(
        current_admin: AdminUser = Depends(lambda: None),  # placeholder, overridden at route level
        db: AsyncSession = Depends(get_db),
        authorization: str = None,
    ):
        # This is used as a dependency, the admin is injected separately
        pass

    # Return a dependency that checks permissions
    from app.dependencies import get_current_admin

    async def permission_checker(
        admin: AdminUser = Depends(get_current_admin),
        db: AsyncSession = Depends(get_db),
    ):
        permissions = await get_admin_permissions(str(admin.id), db)
        for code in permission_codes:
            if code not in permissions:
                raise ForbiddenError(f"缺少权限: {code}")

    return permission_checker


async def invalidate_admin_permissions(admin_id: str) -> None:
    """Invalidate cached permissions when roles change."""
    try:
        await redis_client.delete(f"admin_perms:{admin_id}")
    except Exception:
        pass
