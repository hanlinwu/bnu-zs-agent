"""System configuration APIs for administrators."""

import hashlib
import os

from fastapi import APIRouter, Depends
from fastapi import File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.core.exceptions import BizError
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.services.system_config_service import (
    get_chat_guardrail_config,
    update_chat_guardrail_config,
    get_system_basic_config,
    update_system_basic_config,
    get_system_version_info,
)

router = APIRouter()
ALLOWED_LOGO_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "svg"}
ALLOWED_LOGO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/svg+xml"}


class ChatGuardrailConfigUpdateRequest(BaseModel):
    value: dict = Field(..., description="智能体配置")


class SystemBasicConfigUpdateRequest(BaseModel):
    value: dict = Field(..., description="系统名称与Logo配置")


@router.post("/logo/upload", dependencies=[Depends(require_permission("system_config:update"))])
async def upload_system_logo(
    file: UploadFile = File(...),
    admin: AdminUser = Depends(get_current_admin),
):
    """上传系统Logo图片。"""
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if ext not in ALLOWED_LOGO_EXTENSIONS:
        raise BizError(code=400, message="Logo格式仅支持 JPG/JPEG/PNG/WEBP/SVG")

    if file.content_type and file.content_type not in ALLOWED_LOGO_TYPES:
        raise BizError(code=400, message="仅支持图片文件上传")

    content = await file.read()
    if not content:
        raise BizError(code=400, message="上传文件为空")
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise BizError(code=400, message=f"文件大小超过 {settings.MAX_UPLOAD_SIZE_MB}MB 限制")

    logo_dir = os.path.join(settings.UPLOAD_DIR, "system")
    os.makedirs(logo_dir, exist_ok=True)
    digest = hashlib.sha256(content).hexdigest()[:16]
    filename = f"logo-{digest}.{ext}"
    file_path = os.path.join(logo_dir, filename)
    with open(file_path, "wb") as f:
        f.write(content)

    return {"url": f"/uploads/system/{filename}"}


@router.get("/chat-guardrail", dependencies=[Depends(require_permission("system_config:read"))])
async def get_chat_guardrail(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取智能体配置。"""
    config = await get_chat_guardrail_config(db)
    return {"key": "chat_guardrail", "value": config}


@router.put("/chat-guardrail", dependencies=[Depends(require_permission("system_config:update"))])
async def put_chat_guardrail(
    body: ChatGuardrailConfigUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新智能体配置。"""
    config = await update_chat_guardrail_config(body.value, str(admin.id), db)
    return {"key": "chat_guardrail", "value": config}


@router.get("/basic", dependencies=[Depends(require_permission("system_config:read"))])
async def get_system_basic(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取系统名称与Logo配置。"""
    config = await get_system_basic_config(db)
    return {"key": "system_basic", "value": config, "version": get_system_version_info()}


@router.put("/basic", dependencies=[Depends(require_permission("system_config:update"))])
async def put_system_basic(
    body: SystemBasicConfigUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新系统名称与Logo配置。"""
    config = await update_system_basic_config(body.value, str(admin.id), db)
    return {"key": "system_basic", "value": config, "version": get_system_version_info()}
