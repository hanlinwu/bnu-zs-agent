"""Web search (Tavily) admin API."""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BizError
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.services import tavily_service
from app.services import web_search_config_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request schemas ──────────────────────────────────────────────

class ConfigUpdateRequest(BaseModel):
    value: dict = Field(..., description="Tavily搜索配置")


class ValidateKeyRequest(BaseModel):
    api_key: str | None = None


class SearchRequest(BaseModel):
    query: str
    search_depth: str | None = None
    max_results: int | None = None
    include_domains: list[str] | None = None
    topic: str | None = None


# ── Config endpoints ─────────────────────────────────────────────

@router.get("/config", dependencies=[Depends(require_permission("web_search:read"))])
async def get_config(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取Tavily搜索配置"""
    config = await web_search_config_service.get_config(db)
    config["api_key"] = web_search_config_service._mask_key(config.get("api_key", ""))
    return {"key": web_search_config_service.WEB_SEARCH_CONFIG_KEY, "value": config}


@router.put("/config", dependencies=[Depends(require_permission("web_search:update"))])
async def update_config(
    body: ConfigUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新Tavily搜索配置"""
    config = await web_search_config_service.update_config(
        body.value, str(admin.id), db
    )
    config["api_key"] = web_search_config_service._mask_key(config.get("api_key", ""))
    return {"key": web_search_config_service.WEB_SEARCH_CONFIG_KEY, "value": config}


@router.post("/config/validate", dependencies=[Depends(require_permission("web_search:read"))])
async def validate_api_key(
    body: ValidateKeyRequest = None,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """验证Tavily API Key是否有效"""
    api_key = (body.api_key if body and body.api_key else None) or web_search_config_service.get_api_key()
    if not api_key:
        raise BizError(code=400, message="未配置API Key")

    try:
        valid = await tavily_service.validate_api_key(api_key)
        return {"valid": valid, "message": "API Key有效" if valid else "API Key无效"}
    except Exception as e:
        raise BizError(code=503, message=f"验证失败: {e}", status_code=503)


# ── Search ───────────────────────────────────────────────────────

@router.post("/search", dependencies=[Depends(require_permission("web_search:read"))])
async def search(
    body: SearchRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """执行Tavily搜索测试，所有参数从全局配置读取，请求中的字段仅用于覆盖。"""
    config = await web_search_config_service.get_config(db)

    if not config.get("enabled", True):
        raise BizError(code=400, message="网页搜索功能已关闭，请先在配置中开启")

    api_key = web_search_config_service.get_api_key()
    if not api_key:
        raise BizError(code=400, message="未配置Tavily API Key，请先在配置中设置")

    try:
        result = await tavily_service.search(
            api_key=api_key,
            query=body.query,
            search_depth=body.search_depth or config.get("search_depth", "basic"),
            max_results=body.max_results or config.get("max_results", 10),
            include_domains=body.include_domains if body.include_domains is not None else config.get("include_domains"),
            exclude_domains=config.get("exclude_domains"),
            include_answer=config.get("include_answer", False),
            include_raw_content=config.get("include_raw_content", False),
            topic=body.topic or config.get("topic", "general"),
            country=config.get("country", ""),
            time_range=config.get("time_range", ""),
            chunks_per_source=config.get("chunks_per_source", 3),
            include_images=config.get("include_images", False),
        )
        return result
    except Exception as e:
        # Extract response body from httpx errors for better diagnostics
        detail = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                detail = e.response.text or detail
            except Exception:
                pass
        logger.error("Tavily search failed: %s", detail)
        raise BizError(code=503, message=f"搜索失败: {detail}", status_code=503)
