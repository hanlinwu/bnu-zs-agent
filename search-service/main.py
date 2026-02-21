"""Search microservice — FastAPI application."""

import uuid
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, Header, Query

from config import settings
from database import init_db, get_db
from search_service import meili_service
from scheduler import init_scheduler
from crawl_service import start_crawl_task
from models import (
    CrawlSiteCreate,
    CrawlSiteUpdate,
    CrawlSiteResponse,
    CrawlRequest,
    CrawlTaskResponse,
    SearchRequest,
    SearchResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Auth dependency ──────────────────────────────────────────

async def verify_api_key(authorization: str | None = Header(None)):
    """Simple shared-secret bearer token auth."""
    if not settings.API_KEY:
        return  # No key configured → allow all (dev mode)
    if not authorization or authorization != f"Bearer {settings.API_KEY}":
        raise HTTPException(status_code=401, detail="Invalid API key")


# ── Lifespan ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await meili_service.ensure_index()
    init_scheduler()
    logger.info("Search microservice started")
    yield
    logger.info("Search microservice shutting down")


app = FastAPI(title="BNU Search Service", lifespan=lifespan)


# ── Health ───────────────────────────────────────────────────

@app.get("/health")
async def health():
    try:
        stats = await meili_service.get_stats()
        return {"status": "ok", "meilisearch": stats}
    except Exception as e:
        return {"status": "degraded", "error": str(e)}


# ── Search ───────────────────────────────────────────────────

@app.post("/search", dependencies=[Depends(verify_api_key)])
async def search(body: SearchRequest):
    result = await meili_service.search(
        query=body.query,
        domain=body.domain,
        page=body.page,
        page_size=body.page_size,
    )
    return result


# ── Crawl Tasks ──────────────────────────────────────────────

@app.post("/crawl", dependencies=[Depends(verify_api_key)])
async def trigger_crawl(body: CrawlRequest):
    task_id = await start_crawl_task(
        start_url=body.url,
        max_depth=body.max_depth,
        max_pages=body.max_pages,
        same_domain_only=body.same_domain_only,
        domain_restriction=body.domain_restriction,
        site_id=body.site_id,
    )
    return {"task_id": task_id, "status": "pending"}


@app.get("/crawl/tasks", dependencies=[Depends(verify_api_key)])
async def list_crawl_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    db = await get_db()
    try:
        offset = (page - 1) * page_size
        cursor = await db.execute(
            "SELECT * FROM crawl_tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (page_size, offset),
        )
        tasks = await cursor.fetchall()

        count_cursor = await db.execute("SELECT COUNT(*) FROM crawl_tasks")
        total = (await count_cursor.fetchone())[0]

        return {
            "items": [_task_to_dict(t) for t in tasks],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    finally:
        await db.close()


@app.get("/crawl/{task_id}", dependencies=[Depends(verify_api_key)])
async def get_crawl_task(task_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM crawl_tasks WHERE id = ?", (task_id,))
        task = await cursor.fetchone()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return _task_to_dict(task)
    finally:
        await db.close()


# ── Sites CRUD ───────────────────────────────────────────────

@app.get("/sites", dependencies=[Depends(verify_api_key)])
async def list_sites():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM crawl_sites ORDER BY created_at DESC")
        sites = await cursor.fetchall()
        return {"items": [_site_to_dict(s) for s in sites]}
    finally:
        await db.close()


@app.post("/sites", dependencies=[Depends(verify_api_key)])
async def create_site(body: CrawlSiteCreate):
    db = await get_db()
    try:
        site_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            """INSERT INTO crawl_sites
               (id, domain, name, start_url, max_depth, max_pages, same_domain_only,
                crawl_frequency_minutes, enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                site_id, body.domain, body.name, body.start_url,
                body.max_depth, body.max_pages, int(body.same_domain_only),
                body.crawl_frequency_minutes, int(body.enabled), now, now,
            ),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM crawl_sites WHERE id = ?", (site_id,))
        site = await cursor.fetchone()
        return _site_to_dict(site)
    finally:
        await db.close()


@app.put("/sites/{site_id}", dependencies=[Depends(verify_api_key)])
async def update_site(site_id: str, body: CrawlSiteUpdate):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM crawl_sites WHERE id = ?", (site_id,))
        site = await cursor.fetchone()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")

        updates = {}
        for field in ["name", "start_url", "max_depth", "max_pages", "crawl_frequency_minutes"]:
            val = getattr(body, field, None)
            if val is not None:
                updates[field] = val
        if body.same_domain_only is not None:
            updates["same_domain_only"] = int(body.same_domain_only)
        if body.enabled is not None:
            updates["enabled"] = int(body.enabled)

        if updates:
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            sets = ", ".join(f"{k} = ?" for k in updates)
            vals = list(updates.values()) + [site_id]
            await db.execute(f"UPDATE crawl_sites SET {sets} WHERE id = ?", vals)
            await db.commit()

        cursor = await db.execute("SELECT * FROM crawl_sites WHERE id = ?", (site_id,))
        site = await cursor.fetchone()
        return _site_to_dict(site)
    finally:
        await db.close()


@app.delete("/sites/{site_id}", dependencies=[Depends(verify_api_key)])
async def delete_site(site_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM crawl_sites WHERE id = ?", (site_id,))
        site = await cursor.fetchone()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")

        domain = site["domain"]

        # Delete from SQLite
        await db.execute("DELETE FROM crawl_sites WHERE id = ?", (site_id,))
        await db.commit()

        # Delete indexed documents for this domain
        try:
            await meili_service.delete_by_domain(domain)
        except Exception as e:
            logger.warning("Failed to delete Meilisearch docs for domain %s: %s", domain, e)

        return {"success": True, "message": f"Site {domain} deleted"}
    finally:
        await db.close()


@app.post("/sites/{site_id}/crawl", dependencies=[Depends(verify_api_key)])
async def trigger_site_crawl(site_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM crawl_sites WHERE id = ?", (site_id,))
        site = await cursor.fetchone()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")

        task_id = await start_crawl_task(
            start_url=site["start_url"],
            max_depth=site["max_depth"],
            max_pages=site["max_pages"],
            same_domain_only=bool(site["same_domain_only"]),
            domain_restriction=site["domain"],
            site_id=site_id,
        )
        return {"task_id": task_id, "status": "pending"}
    finally:
        await db.close()


# ── Helpers ──────────────────────────────────────────────────

def _site_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "domain": row["domain"],
        "name": row["name"],
        "start_url": row["start_url"],
        "max_depth": row["max_depth"],
        "max_pages": row["max_pages"],
        "same_domain_only": bool(row["same_domain_only"]),
        "crawl_frequency_minutes": row["crawl_frequency_minutes"],
        "enabled": bool(row["enabled"]),
        "last_crawl_at": row["last_crawl_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _task_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "site_id": row["site_id"],
        "start_url": row["start_url"],
        "status": row["status"],
        "progress": row["progress"],
        "total_pages": row["total_pages"],
        "success_pages": row["success_pages"],
        "failed_pages": row["failed_pages"],
        "error_message": row["error_message"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "created_at": row["created_at"],
    }
