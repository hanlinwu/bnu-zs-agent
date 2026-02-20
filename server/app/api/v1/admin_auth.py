"""Admin authentication routes."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.config import settings
from app.core.database import get_db
from app.core.exceptions import UnauthorizedError, BizError
from app.core.security import verify_password, verify_mfa_code, create_access_token
from app.core.permissions import get_admin_permissions
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.schemas.admin import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminInfoResponse,
    AdminSmsSendRequest,
    AdminBindPhoneSendRequest,
    AdminBindPhoneConfirmRequest,
)
from app.services.sms_service import send_sms_code, verify_sms_code

router = APIRouter()


def _mask_phone(phone: str | None) -> str:
    if not phone or len(phone) < 7:
        return ""
    return f"{phone[:3]}****{phone[-4:]}"


def _raise_sms_send_error(message: str) -> None:
    if "频繁" in message or "超限" in message:
        raise BizError(code=429, message=message, status_code=429)
    raise BizError(code=400, message=message)


def _need_phone_sms_verification(admin: AdminUser, current_ip: str | None, now: datetime) -> bool:
    if not admin.phone:
        return False
    if not admin.last_login_at:
        # First login always requires phone verification when phone exists.
        return True

    last_ip = str(admin.last_login_ip) if admin.last_login_ip else ""
    # Historical login exists but IP baseline is missing: force one-time SMS check.
    if not last_ip:
        return True

    ip_changed = bool(current_ip and last_ip and current_ip != last_ip)
    hours_since_last_login = (now - admin.last_login_at).total_seconds() / 3600

    if ip_changed and hours_since_last_login >= settings.ADMIN_PHONE_VERIFY_IP_CHANGE_HOURS:
        return True
    if hours_since_last_login >= settings.ADMIN_PHONE_VERIFY_IDLE_HOURS:
        return True
    return False


def _build_login_response(admin: AdminUser, token: str) -> AdminLoginResponse:
    return AdminLoginResponse(
        success=True,
        token=token,
        admin={
            "id": str(admin.id),
            "username": admin.username,
            "real_name": admin.real_name,
        },
    )


@router.post("/phone/bind/send")
async def admin_bind_phone_send_code(
    body: AdminBindPhoneSendRequest,
    db: AsyncSession = Depends(get_db),
):
    """首次登录手机号绑定：发送验证码。"""
    result = await db.execute(select(AdminUser).where(AdminUser.username == body.username))
    admin = result.scalar_one_or_none()

    if not admin or admin.status != "active" or not verify_password(body.password, admin.password_hash):
        raise UnauthorizedError("用户名或密码错误")

    if admin.phone:
        raise BizError(code=400, message="当前账号已绑定手机号，请直接使用登录验证码流程")

    send_result = await send_sms_code(body.phone)
    if not send_result.get("success"):
        _raise_sms_send_error(send_result.get("message") or "验证码发送失败")

    return {
        "success": True,
        "message": send_result.get("message") or "验证码已发送",
        "phone_masked": _mask_phone(body.phone),
    }


@router.post("/phone/bind/confirm", response_model=AdminLoginResponse)
async def admin_bind_phone_confirm(
    body: AdminBindPhoneConfirmRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """首次登录手机号绑定并完成登录。"""
    result = await db.execute(select(AdminUser).where(AdminUser.username == body.username))
    admin = result.scalar_one_or_none()

    if not admin or admin.status != "active" or not verify_password(body.password, admin.password_hash):
        raise UnauthorizedError("用户名或密码错误")

    if admin.phone and admin.phone != body.phone:
        raise UnauthorizedError("当前账号已绑定其他手机号")

    if admin.mfa_secret:
        if not body.mfa_code:
            raise UnauthorizedError("需要 MFA 验证码")
        if not verify_mfa_code(admin.mfa_secret, body.mfa_code):
            raise UnauthorizedError("MFA 验证码错误")

    if not await verify_sms_code(body.phone, body.sms_code):
        raise UnauthorizedError("手机号验证码错误或已过期")

    admin.phone = body.phone

    expire_delta = timedelta(hours=settings.ADMIN_TOKEN_EXPIRE_HOURS)
    token = create_access_token(
        {"sub": str(admin.id), "type": "admin"},
        expires_delta=expire_delta,
    )

    now = datetime.now(timezone.utc)
    admin.last_login_at = now
    admin.last_login_ip = request.client.host if request.client else None
    admin.token_expire_at = now + expire_delta
    await db.commit()

    return _build_login_response(admin, token)


@router.post("/sms/send")
async def admin_send_sms_code(
    body: AdminSmsSendRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """管理员登录二次验证短信发送。"""
    result = await db.execute(select(AdminUser).where(AdminUser.username == body.username))
    admin = result.scalar_one_or_none()

    if not admin or admin.status != "active" or not verify_password(body.password, admin.password_hash):
        raise UnauthorizedError("用户名或密码错误")

    current_ip = request.client.host if request.client else None
    now = datetime.now(timezone.utc)
    if not _need_phone_sms_verification(admin, current_ip, now):
        return {"success": True, "required": False, "message": "当前登录无需手机号验证"}

    if not admin.phone:
        raise BizError(code=400, message="首次登录需绑定手机号")

    send_result = await send_sms_code(admin.phone)
    if not send_result.get("success"):
        _raise_sms_send_error(send_result.get("message") or "验证码发送失败")

    return {
        "success": True,
        "required": True,
        "phone_masked": _mask_phone(admin.phone),
        "message": send_result.get("message") or "验证码已发送",
    }


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

    # Verify phone SMS code if risk check requires
    current_ip = request.client.host if request.client else None
    now = datetime.now(timezone.utc)
    if _need_phone_sms_verification(admin, current_ip, now):
        if not admin.phone:
            raise BizError(code=400, message="首次登录需绑定手机号")
        if not body.sms_code:
            raise UnauthorizedError("需要手机号验证码")
        if not await verify_sms_code(admin.phone, body.sms_code):
            raise UnauthorizedError("手机号验证码错误或已过期")

    # Generate token
    expire_delta = timedelta(hours=settings.ADMIN_TOKEN_EXPIRE_HOURS)
    token = create_access_token(
        {"sub": str(admin.id), "type": "admin"},
        expires_delta=expire_delta,
    )

    # Update login info
    admin.last_login_at = now
    admin.last_login_ip = current_ip
    admin.token_expire_at = now + expire_delta
    await db.commit()

    return _build_login_response(admin, token)


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
