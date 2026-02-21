"""Web crawler using Crawl4AI with BFS traversal."""

import asyncio
import logging
import uuid
from collections import deque
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import aiosqlite
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

from config import settings
from database import get_db
from search_service import meili_service, url_to_doc_id

logger = logging.getLogger(__name__)

# Track running crawl tasks so we can report status
_running_tasks: dict[str, asyncio.Task] = {}


async def _update_task(db: aiosqlite.Connection, task_id: str, **fields):
    """Update crawl task fields in SQLite."""
    sets = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values())
    vals.append(task_id)
    await db.execute(f"UPDATE crawl_tasks SET {sets} WHERE id = ?", vals)
    await db.commit()


def _same_domain(url: str, domain: str) -> bool:
    """Check if url belongs to the given domain (including subdomains)."""
    host = urlparse(url).netloc.lower()
    domain = domain.lower()
    return host == domain or host.endswith("." + domain)


async def run_crawl(
    task_id: str,
    start_url: str,
    max_depth: int,
    max_pages: int,
    same_domain_only: bool,
    domain_restriction: str | None = None,
):
    """BFS crawl from start_url, indexing each page into Meilisearch."""
    db = await get_db()
    try:
        now = datetime.now(timezone.utc).isoformat()
        await _update_task(db, task_id, status="running", started_at=now)

        base_domain = domain_restriction or urlparse(start_url).netloc.lower()
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(start_url, 0)])
        success = 0
        failed = 0
        batch: list[dict] = []

        browser_config = BrowserConfig(headless=True, verbose=False)
        crawl_config = CrawlerRunConfig(
            word_count_threshold=10,
            excluded_tags=["nav", "footer", "header"],
            exclude_external_links=same_domain_only,
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            while queue and (success + failed) < max_pages:
                url, depth = queue.popleft()

                # Normalise and dedup
                url = url.split("#")[0].rstrip("/")
                if url in visited:
                    continue
                visited.add(url)

                # Domain check
                if same_domain_only and not _same_domain(url, base_domain):
                    continue

                # Update current progress
                await _update_task(
                    db, task_id,
                    progress=int((success + failed) / max(max_pages, 1) * 100),
                    total_pages=len(visited),
                    success_pages=success,
                    failed_pages=failed,
                )

                try:
                    result = await crawler.arun(url=url, config=crawl_config)

                    if result.success and result.markdown:
                        doc = {
                            "id": url_to_doc_id(url),
                            "url": url,
                            "title": result.metadata.get("title", url) if result.metadata else url,
                            "content": result.markdown[:50000],  # Cap content length
                            "domain": base_domain,
                            "crawled_at": datetime.now(timezone.utc).isoformat(),
                        }
                        batch.append(doc)
                        success += 1

                        # Flush batch every 10 documents
                        if len(batch) >= 10:
                            await meili_service.index_pages(batch)
                            batch = []

                        # Enqueue discovered links if not at max depth
                        if depth < max_depth and result.links:
                            internal = result.links.get("internal", [])
                            for link_info in internal:
                                href = link_info.get("href", "") if isinstance(link_info, dict) else str(link_info)
                                abs_url = urljoin(url, href).split("#")[0].rstrip("/")
                                if abs_url not in visited:
                                    queue.append((abs_url, depth + 1))
                    else:
                        failed += 1

                except Exception as e:
                    logger.warning("Failed to crawl %s: %s", url, e)
                    failed += 1

                # Polite delay
                if settings.CRAWL_DELAY_MS > 0:
                    await asyncio.sleep(settings.CRAWL_DELAY_MS / 1000)

        # Flush remaining batch
        if batch:
            await meili_service.index_pages(batch)

        finished_at = datetime.now(timezone.utc).isoformat()
        await _update_task(
            db, task_id,
            status="success",
            progress=100,
            total_pages=len(visited),
            success_pages=success,
            failed_pages=failed,
            finished_at=finished_at,
        )
        logger.info("Crawl %s done: %d success, %d failed", task_id, success, failed)

    except Exception as e:
        logger.exception("Crawl %s failed: %s", task_id, e)
        await _update_task(
            db, task_id,
            status="failed",
            error_message=str(e)[:2000],
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
    finally:
        await db.close()
        _running_tasks.pop(task_id, None)


async def start_crawl_task(
    start_url: str,
    max_depth: int = 3,
    max_pages: int = 100,
    same_domain_only: bool = True,
    domain_restriction: str | None = None,
    site_id: str | None = None,
) -> str:
    """Create a crawl task record and start it in the background. Returns task ID."""
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO crawl_tasks
               (id, site_id, start_url, max_depth, max_pages, same_domain_only, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)""",
            (task_id, site_id, start_url, max_depth, max_pages, int(same_domain_only), now),
        )
        await db.commit()
    finally:
        await db.close()

    # Update site's last_crawl_at
    if site_id:
        db = await get_db()
        try:
            await db.execute(
                "UPDATE crawl_sites SET last_crawl_at = ? WHERE id = ?", (now, site_id)
            )
            await db.commit()
        finally:
            await db.close()

    # Launch background crawl
    task = asyncio.create_task(
        run_crawl(task_id, start_url, max_depth, max_pages, same_domain_only, domain_restriction)
    )
    _running_tasks[task_id] = task
    return task_id
