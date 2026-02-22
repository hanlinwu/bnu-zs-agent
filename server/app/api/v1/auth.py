"""User authentication routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import (
    SmsSendRequest, SmsSendResponse,
    LoginRequest, LoginResponse,
    UserInfoResponse, UserUpdateRequest,
)
from app.services.sms_service import send_sms_code
from app.services.auth_service import login_or_register
from app.services.request_ip_service import get_client_ip

router = APIRouter()
ALLOWED_STAGES = {"undergraduate", "master", "doctor"}


def _parse_stages(raw: str | None) -> list[str]:
    if not raw:
        return []
    items = [part.strip() for part in str(raw).split(",") if part.strip()]
    result: list[str] = []
    for item in items:
        if item in ALLOWED_STAGES and item not in result:
            result.append(item)
    return result


def _serialize_stages(items: list[str] | None) -> str | None:
    if not isinstance(items, list):
        return None
    result: list[str] = []
    for item in items:
        val = str(item).strip()
        if val in ALLOWED_STAGES and val not in result:
            result.append(val)
    return ",".join(result) if result else ""


@router.post("/sms/send", response_model=SmsSendResponse)
async def api_send_sms(body: SmsSendRequest):
    """发送短信验证码"""
    result = await send_sms_code(body.phone, purpose="user_login")
    return result


@router.post("/login", response_model=LoginResponse)
async def api_login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """短信验证码登录/注册"""
    ip = get_client_ip(request)
    result = await login_or_register(
        phone=body.phone,
        code=body.code,
        nickname=body.nickname,
        user_role=body.user_role,
        ip=ip,
        db=db,
    )
    return result


@router.post("/logout")
async def api_logout(current_user: User = Depends(get_current_user)):
    """用户登出"""
    # In production, add token to blacklist in Redis
    return {"success": True, "message": "已登出"}


@router.get("/me", response_model=UserInfoResponse)
async def api_get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserInfoResponse(
        id=str(current_user.id),
        phone=current_user.phone,
        nickname=current_user.nickname,
        avatar_url=current_user.avatar_url or "",
        gender=current_user.gender,
        province=current_user.province,
        admission_stages=_parse_stages(current_user.admission_stages),
        identity_type=current_user.identity_type,
        source_group=current_user.source_group,
        birth_year=current_user.birth_year,
        school=current_user.school,
        status=current_user.status,
    )


@router.put("/me", response_model=UserInfoResponse)
async def api_update_me(
    body: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新当前用户信息"""
    update_data = body.model_dump(exclude_unset=True)
    if "admission_stages" in update_data:
        update_data["admission_stages"] = _serialize_stages(update_data.get("admission_stages"))
    for key, value in update_data.items():
        setattr(current_user, key, value)
    current_user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(current_user)

    return UserInfoResponse(
        id=str(current_user.id),
        phone=current_user.phone,
        nickname=current_user.nickname,
        avatar_url=current_user.avatar_url or "",
        gender=current_user.gender,
        province=current_user.province,
        admission_stages=_parse_stages(current_user.admission_stages),
        identity_type=current_user.identity_type,
        source_group=current_user.source_group,
        birth_year=current_user.birth_year,
        school=current_user.school,
        status=current_user.status,
    )
