"""User authentication service."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ForbiddenError
from app.core.security import create_access_token
from app.models.user import User
from app.services.ip_location_service import detect_province_by_ip
from app.services.sms_service import verify_sms_code


async def login_or_register(
    phone: str,
    code: str,
    nickname: str | None,
    user_role: str | None,
    ip: str | None,
    db: AsyncSession,
) -> dict:
    """Verify SMS code and login or register user."""
    # Verify SMS code
    if not await verify_sms_code(phone, code, purpose="user_login"):
        return {"success": False, "message": "验证码错误或已过期"}

    # Check if user exists
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    if user:
        if user.status != "active":
            raise ForbiddenError("账号已被禁用，请联系客服")
        is_first_login = user.last_login_at is None
    else:
        # Register new user
        if not nickname:
            nickname = f"用户{phone[-4:]}"
        user = User(
            phone=phone,
            nickname=nickname,
            status="active",
        )
        db.add(user)
        await db.flush()
        is_first_login = True

        # User role selection is deprecated; keep a unified user role model.

    # Generate token
    expire_delta = timedelta(days=settings.USER_TOKEN_EXPIRE_DAYS)
    token = create_access_token(
        {"sub": str(user.id), "type": "user"},
        expires_delta=expire_delta,
    )

    # Update login info
    now = datetime.now(timezone.utc)
    user.last_login_at = now
    user.last_login_ip = ip
    detected_province = await detect_province_by_ip(ip)
    if detected_province:
        user.province = detected_province
    user.token_expire_at = now + expire_delta

    await db.commit()
    await db.refresh(user)

    return {
        "success": True,
        "token": token,
        "is_first_login": is_first_login,
        "user": {
            "id": str(user.id),
            "phone": user.phone,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url,
            "province": user.province,
            "admission_stages": [s for s in (user.admission_stages or "").split(",") if s],
            "identity_type": user.identity_type,
            "source_group": user.source_group,
            "status": user.status,
        },
    }
