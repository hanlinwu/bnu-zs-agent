"""System configuration APIs for administrators."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.services.system_config_service import get_chat_guardrail_config, update_chat_guardrail_config

router = APIRouter()


class ChatGuardrailConfigUpdateRequest(BaseModel):
    value: dict = Field(..., description="聊天风险判定与分级提示词配置")


@router.get("/chat-guardrail", dependencies=[Depends(require_permission("system_config:read"))])
async def get_chat_guardrail(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取聊天风险判定与Prompt配置。"""
    config = await get_chat_guardrail_config(db)
    return {"key": "chat_guardrail", "value": config}


@router.put("/chat-guardrail", dependencies=[Depends(require_permission("system_config:update"))])
async def put_chat_guardrail(
    body: ChatGuardrailConfigUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新聊天风险判定与Prompt配置。"""
    config = await update_chat_guardrail_config(body.value, str(admin.id), db)
    return {"key": "chat_guardrail", "value": config}
