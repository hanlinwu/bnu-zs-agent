"""Admin authentication routes."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.config import settings
from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import verify_password, verify_mfa_code, create_access_token
from app.core.permissions import get_admin_permissions
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.schemas.admin import AdminLoginRequest, AdminLoginResponse, AdminInfoResponse

router = APIRouter()


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(body: AdminLoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """管理员登录（用户名 + 密码 + MFA）"""
    # Find admin by username
    result = await db.execute(select(AdminUser).where(AdminUser.username == body.username))
    admin = result.scalar_one_or_none()

    if not admin:
        raise UnauthorizedError("用户名或密码错误")

    if admin.status != "active":
        raise UnauthorizedError("账号已被禁用")

    # Verify password
    if not verify_password(body.password, admin.password_hash):
        raise UnauthorizedError("用户名或密码错误")

    # Verify MFA if enabled
    if admin.mfa_secret:
        if not body.mfa_code:
            raise UnauthorizedError("需要 MFA 验证码")
        if not verify_mfa_code(admin.mfa_secret, body.mfa_code):
            raise UnauthorizedError("MFA 验证码错误")

    # Generate token
    expire_delta = timedelta(hours=settings.ADMIN_TOKEN_EXPIRE_HOURS)
    token = create_access_token(
        {"sub": str(admin.id), "type": "admin"},
        expires_delta=expire_delta,
    )

    # Update login info
    now = datetime.now(timezone.utc)
    admin.last_login_at = now
    admin.last_login_ip = request.client.host if request.client else None
    admin.token_expire_at = now + expire_delta
    await db.commit()

    return AdminLoginResponse(
        success=True,
        token=token,
        admin={
            "id": str(admin.id),
            "username": admin.username,
            "real_name": admin.real_name,
        },
    )


@router.post("/logout")
async def admin_logout(admin: AdminUser = Depends(get_current_admin)):
    """管理员登出"""
    return {"success": True, "message": "已登出"}


@router.get("/me", response_model=AdminInfoResponse)
async def admin_get_me(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取管理员信息 + 权限列表"""
    permissions = await get_admin_permissions(str(admin.id), db)

    return AdminInfoResponse(
        id=str(admin.id),
        username=admin.username,
        real_name=admin.real_name,
        employee_id=admin.employee_id,
        department=admin.department,
        title=admin.title,
        phone=admin.phone,
        email=admin.email,
        avatar_url=admin.avatar_url or "",
        status=admin.status,
        permissions=sorted(permissions),
    )
