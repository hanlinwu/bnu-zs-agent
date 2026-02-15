"""Model configuration API for administrators."""

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.core.exceptions import BizError
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser

router = APIRouter()


class ModelConfigUpdate(BaseModel):
    primary_provider: str | None = None
    primary_api_key: str | None = None
    primary_base_url: str | None = None
    primary_model: str | None = None
    review_provider: str | None = None
    review_model: str | None = None


class ModelTestRequest(BaseModel):
    provider: str
    api_key: str
    base_url: str
    model: str


@router.get("", dependencies=[Depends(require_permission("model:read"))])
async def get_model_config(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取当前模型配置"""
    return {
        "primary_provider": settings.LLM_PRIMARY_PROVIDER,
        "primary_api_key": _mask_key(settings.LLM_PRIMARY_API_KEY),
        "primary_base_url": settings.LLM_PRIMARY_BASE_URL,
        "primary_model": settings.LLM_PRIMARY_MODEL,
        "review_provider": settings.LLM_REVIEW_PROVIDER,
        "review_model": settings.LLM_REVIEW_MODEL,
    }


@router.put("", dependencies=[Depends(require_permission("model:update"))])
async def update_model_config(
    body: ModelConfigUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新模型配置（运行时热更新）"""
    if body.primary_provider is not None:
        settings.LLM_PRIMARY_PROVIDER = body.primary_provider
    if body.primary_api_key is not None:
        settings.LLM_PRIMARY_API_KEY = body.primary_api_key
    if body.primary_base_url is not None:
        settings.LLM_PRIMARY_BASE_URL = body.primary_base_url
    if body.primary_model is not None:
        settings.LLM_PRIMARY_MODEL = body.primary_model
    if body.review_provider is not None:
        settings.LLM_REVIEW_PROVIDER = body.review_provider
    if body.review_model is not None:
        settings.LLM_REVIEW_MODEL = body.review_model

    # Rebuild the LLM router with updated settings
    from app.services.llm_service import create_llm_router, llm_router as _old
    import app.services.llm_service as llm_mod
    llm_mod.llm_router = create_llm_router()

    return {"success": True, "message": "模型配置已更新"}


@router.post("/test", dependencies=[Depends(require_permission("model:update"))])
async def test_model_connectivity(
    body: ModelTestRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """测试模型连通性"""
    base_url = body.base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {body.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": body.model,
        "messages": [{"role": "user", "content": "你好"}],
        "max_tokens": 16,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            reply = data["choices"][0]["message"]["content"]
    except httpx.TimeoutException:
        raise BizError(code=400, message="连接超时，请检查 Base URL 和网络")
    except httpx.HTTPStatusError as e:
        raise BizError(code=400, message=f"API 返回错误: {e.response.status_code}")
    except Exception as e:
        raise BizError(code=400, message=f"连接失败: {str(e)}")

    return {
        "success": True,
        "message": "连接成功",
        "reply": reply,
        "provider": body.provider,
        "model": body.model,
    }


def _mask_key(key: str) -> str:
    """Mask API key, showing only first 4 and last 4 characters."""
    if not key or len(key) <= 8:
        return "****"
    return f"{key[:4]}****{key[-4:]}"
