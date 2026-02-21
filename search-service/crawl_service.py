"""Web crawler using Crawl4AI with BFS traversal."""

import asyncio
import logging
import re
import uuid
from asyncio.subprocess import PIPE
from collections import deque
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urljoin, urlparse

import aiosqlite
import httpx
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


def _normalize_domain(domain_or_url: str) -> str:
    """Normalize domain or URL into a lower-case hostname."""
    if not domain_or_url:
        return ""
    s = domain_or_url.strip().lower()
    if "://" in s:
        s = urlparse(s).netloc or s
    else:
        # Handle accidental path-like input without scheme.
        s = s.split("/", 1)[0]
    return s.strip()


def _html_to_text(html: str) -> str:
    """Best-effort HTML to plain text for fallback indexing."""
    if not html:
        return ""
    text = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\\1>", " ", html)
    text = re.sub(r"(?is)<br\\s*/?>", "\n", text)
    text = re.sub(r"(?is)</(p|div|li|h[1-6]|tr|section|article)>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"[ \\t\\r\\f\\v]+", " ", text)
    text = re.sub(r"\\n{2,}", "\n", text)
    return text.strip()


def _extract_title(html: str) -> str | None:
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html or "")
    if not m:
        return None
    return unescape(m.group(1)).strip()


async def _fallback_fetch_page(url: str) -> tuple[str | None, str | None]:
    """Fallback fetch via HTTP when browser crawling fails."""
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                return None, None
            html = resp.text or ""
            title = _extract_title(html)
            text = _html_to_text(html)
            if len(text) < 20:
                return title, None
            return title, text
    except Exception as e:
        logger.warning("HTTP fallback failed for %s: %s", url, e)

    # In some environments Playwright/httpx TLS stacks fail while curl still works.
    # Try curl as a final fallback to keep indexing available.
    try:
        proc = await asyncio.create_subprocess_exec(
            "curl",
            "-fsSL",
            "--max-time",
            "20",
            "-A",
            (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            ),
            url,
            stdout=PIPE,
            stderr=PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.warning(
                "Curl fallback failed for %s: rc=%s err=%s",
                url,
                proc.returncode,
                (stderr or b"").decode(errors="ignore")[:200],
            )
            return None, None

        html = (stdout or b"").decode(errors="ignore")
        title = _extract_title(html)
        text = _html_to_text(html)
        if len(text) < 20:
            return title, None
        return title, text
    except FileNotFoundError:
        logger.warning("Curl is not installed; cannot run curl fallback for %s", url)
        return None, None
    except Exception as e:
        logger.warning("Unexpected curl fallback error for %s: %s", url, e)
        return None, None


def _same_domain(url: str, domain: str) -> bool:
    """Check if url belongs to the given domain (including subdomains)."""
    host = urlparse(url).netloc.lower()
    domain = _normalize_domain(domain)
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

        base_domain = _normalize_domain(domain_restriction or urlparse(start_url).netloc)
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
                    page_title = url
                    page_content = ""
                    discovered_links = []

                    if result.success and result.markdown:
                        page_title = result.metadata.get("title", url) if result.metadata else url
                        page_content = result.markdown
                        discovered_links = (result.links or {}).get("internal", [])
                    elif result.success and getattr(result, "cleaned_html", None):
                        page_title = result.metadata.get("title", url) if result.metadata else url
                        page_content = _html_to_text(result.cleaned_html)
                        discovered_links = (result.links or {}).get("internal", [])
                    else:
                        fb_title, fb_text = await _fallback_fetch_page(url)
                        if fb_text:
                            page_title = fb_title or (result.metadata.get("title", url) if result and result.metadata else url)
                            page_content = fb_text
                        else:
                            err = getattr(result, "error_message", None)
                            logger.warning("No indexable content for %s (crawler_success=%s, error=%s)", url, result.success, err)

                    if page_content:
                        doc = {
                            "id": url_to_doc_id(url),
                            "url": url,
                            "title": page_title,
                            "content": page_content[:50000],  # Cap content length
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
                        if depth < max_depth and discovered_links:
                            internal = discovered_links
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
