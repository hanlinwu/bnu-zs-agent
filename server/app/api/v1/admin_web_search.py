"""Web search microservice management API."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError, BizError
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.models.web_search import WebSearchSite
from app.services import search_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request schemas ──────────────────────────────────────────

class SiteCreateRequest(BaseModel):
    domain: str
    name: str
    start_url: str
    max_depth: int = 3
    max_pages: int = 100
    same_domain_only: bool = True
    crawl_frequency_minutes: int = 1440
    enabled: bool = True


class SiteUpdateRequest(BaseModel):
    name: str | None = None
    start_url: str | None = None
    max_depth: int | None = None
    max_pages: int | None = None
    same_domain_only: bool | None = None
    crawl_frequency_minutes: int | None = None
    enabled: bool | None = None


class SearchQueryRequest(BaseModel):
    query: str
    domain: str | None = None
    page: int = 1
    page_size: int = 20


# ── Site CRUD ────────────────────────────────────────────────

@router.get("/sites", dependencies=[Depends(require_permission("web_search:read"))])
async def list_sites(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """列出所有搜索站点配置"""
    result = await db.execute(
        select(WebSearchSite).order_by(WebSearchSite.created_at.desc())
    )
    sites = result.scalars().all()
    return {"items": [_serialize_site(s) for s in sites]}


@router.post("/sites", dependencies=[Depends(require_permission("web_search:create"))])
async def create_site(
    body: SiteCreateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建搜索站点"""
    site = WebSearchSite(
        domain=body.domain,
        name=body.name,
        start_url=body.start_url,
        max_depth=body.max_depth,
        max_pages=body.max_pages,
        same_domain_only=body.same_domain_only,
        crawl_frequency_minutes=body.crawl_frequency_minutes,
        enabled=body.enabled,
        created_by=admin.id,
    )
    db.add(site)
    await db.commit()
    await db.refresh(site)

    # Sync to search microservice
    try:
        remote = await search_client.create_site({
            "domain": body.domain,
            "name": body.name,
            "start_url": body.start_url,
            "max_depth": body.max_depth,
            "max_pages": body.max_pages,
            "same_domain_only": body.same_domain_only,
            "crawl_frequency_minutes": body.crawl_frequency_minutes,
            "enabled": body.enabled,
        })
        site.remote_site_id = remote.get("id")
        await db.commit()
    except Exception as e:
        logger.warning("Failed to sync site to search service: %s", e)

    return _serialize_site(site)


@router.put("/sites/{site_id}", dependencies=[Depends(require_permission("web_search:update"))])
async def update_site(
    site_id: str,
    body: SiteUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新搜索站点配置"""
    result = await db.execute(select(WebSearchSite).where(WebSearchSite.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        raise NotFoundError("站点不存在")

    update_data = {}
    for field in ["name", "start_url", "max_depth", "max_pages", "same_domain_only",
                  "crawl_frequency_minutes", "enabled"]:
        val = getattr(body, field, None)
        if val is not None:
            setattr(site, field, val)
            update_data[field] = val

    site.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(site)

    # Sync to search microservice
    if site.remote_site_id and update_data:
        try:
            await search_client.update_site(site.remote_site_id, update_data)
        except Exception as e:
            logger.warning("Failed to sync site update to search service: %s", e)

    return _serialize_site(site)


@router.delete("/sites/{site_id}", dependencies=[Depends(require_permission("web_search:delete"))])
async def delete_site(
    site_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除搜索站点"""
    result = await db.execute(select(WebSearchSite).where(WebSearchSite.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        raise NotFoundError("站点不存在")

    # Delete from search microservice
    if site.remote_site_id:
        try:
            await search_client.delete_site(site.remote_site_id)
        except Exception as e:
            logger.warning("Failed to delete site from search service: %s", e)

    await db.delete(site)
    await db.commit()
    return {"success": True, "message": "站点已删除"}


# ── Crawl operations ────────────────────────────────────────

@router.post("/sites/{site_id}/crawl", dependencies=[Depends(require_permission("web_search:create"))])
async def trigger_site_crawl(
    site_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """手动触发站点爬取"""
    result = await db.execute(select(WebSearchSite).where(WebSearchSite.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        raise NotFoundError("站点不存在")

    if not site.remote_site_id:
        # Try to sync the site first
        try:
            remote = await search_client.create_site({
                "domain": site.domain,
                "name": site.name,
                "start_url": site.start_url,
                "max_depth": site.max_depth,
                "max_pages": site.max_pages,
                "same_domain_only": site.same_domain_only,
                "crawl_frequency_minutes": site.crawl_frequency_minutes,
                "enabled": site.enabled,
            })
            site.remote_site_id = remote.get("id")
            await db.commit()
        except Exception as e:
            raise BizError(code=503, message=f"搜索微服务不可用: {e}", status_code=503)

    try:
        resp = await search_client.trigger_crawl(site.remote_site_id)
        site.last_crawl_at = datetime.now(timezone.utc)
        site.last_crawl_status = "running"
        await db.commit()
        return resp
    except Exception as e:
        raise BizError(code=503, message=f"触发爬取失败: {e}", status_code=503)


@router.get("/crawl-tasks", dependencies=[Depends(require_permission("web_search:read"))])
async def list_crawl_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: AdminUser = Depends(get_current_admin),
):
    """获取爬取任务列表"""
    try:
        return await search_client.list_crawl_tasks(page, page_size)
    except Exception as e:
        raise BizError(code=503, message=f"搜索微服务不可用: {e}", status_code=503)


@router.get("/crawl-tasks/{task_id}", dependencies=[Depends(require_permission("web_search:read"))])
async def get_crawl_task(
    task_id: str,
    admin: AdminUser = Depends(get_current_admin),
):
    """获取爬取任务详情"""
    try:
        return await search_client.get_crawl_task(task_id)
    except Exception as e:
        raise BizError(code=503, message=f"搜索微服务不可用: {e}", status_code=503)


# ── Search proxy ─────────────────────────────────────────────

@router.post("/search", dependencies=[Depends(require_permission("web_search:read"))])
async def search_query(
    body: SearchQueryRequest,
    admin: AdminUser = Depends(get_current_admin),
):
    """搜索代理 — 转发到微服务"""
    try:
        return await search_client.search(
            query=body.query,
            domain=body.domain,
            page=body.page,
            page_size=body.page_size,
        )
    except Exception as e:
        raise BizError(code=503, message=f"搜索微服务不可用: {e}", status_code=503)


# ── Health check ─────────────────────────────────────────────

@router.get("/health", dependencies=[Depends(require_permission("web_search:read"))])
async def microservice_health(
    admin: AdminUser = Depends(get_current_admin),
):
    """检查搜索微服务健康状态"""
    try:
        return await search_client.health_check()
    except Exception as e:
        raise BizError(code=503, message=f"搜索微服务不可用: {str(e)}", status_code=503)


# ── Helpers ──────────────────────────────────────────────────

def _serialize_site(site: WebSearchSite) -> dict:
    return {
        "id": str(site.id),
        "domain": site.domain,
        "name": site.name,
        "start_url": site.start_url,
        "max_depth": site.max_depth,
        "max_pages": site.max_pages,
        "same_domain_only": site.same_domain_only,
        "crawl_frequency_minutes": site.crawl_frequency_minutes,
        "enabled": site.enabled,
        "remote_site_id": site.remote_site_id,
        "last_crawl_at": site.last_crawl_at.isoformat() if site.last_crawl_at else None,
        "last_crawl_status": site.last_crawl_status,
        "created_at": site.created_at.isoformat(),
        "updated_at": site.updated_at.isoformat(),
    }
