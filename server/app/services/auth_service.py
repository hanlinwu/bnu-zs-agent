"""User authentication service."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ForbiddenError
from app.core.security import create_access_token
from app.models.user import User
from app.models.role import UserRole, Role
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
    if not await verify_sms_code(phone, code):
        return {"success": False, "message": "验证码错误或已过期"}

    # Check if user exists
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    if user:
        if user.status != "active":
            raise ForbiddenError("账号已被禁用，请联系客服")
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

        # Assign user role if provided
        if user_role:
            role_result = await db.execute(
                select(Role).where(Role.code == user_role, Role.role_type == "user")
            )
            role = role_result.scalar_one_or_none()
            if role:
                db.add(UserRole(user_id=user.id, role_id=role.id))

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
    user.token_expire_at = now + expire_delta

    await db.commit()
    await db.refresh(user)

    return {
        "success": True,
        "token": token,
        "user": {
            "id": str(user.id),
            "phone": user.phone,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url,
            "status": user.status,
        },
    }
