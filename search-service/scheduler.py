"""Periodic re-crawl scheduler using APScheduler."""

import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import get_db
from crawl_service import start_crawl_task

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def _normalize_domain(domain_or_url: str) -> str:
    s = (domain_or_url or "").strip().lower()
    if "://" in s:
        from urllib.parse import urlparse
        s = urlparse(s).netloc or s
    else:
        s = s.split("/", 1)[0]
    return s


async def check_and_schedule_crawls():
    """Check all enabled crawl sites and trigger re-crawl if overdue."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM crawl_sites WHERE enabled = 1"
        )
        sites = await cursor.fetchall()

        now = datetime.now(timezone.utc)
        for site in sites:
            freq_minutes = site["crawl_frequency_minutes"]
            last_crawl = site["last_crawl_at"]

            if last_crawl:
                last_dt = datetime.fromisoformat(last_crawl)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                if now - last_dt < timedelta(minutes=freq_minutes):
                    continue  # Not yet due

            logger.info(
                "Scheduling crawl for site %s (%s)", site["name"] or site["domain"], site["domain"]
            )
            await start_crawl_task(
                start_url=site["start_url"],
                max_depth=site["max_depth"],
                max_pages=site["max_pages"],
                same_domain_only=bool(site["same_domain_only"]),
                domain_restriction=_normalize_domain(site["domain"]),
                site_id=site["id"],
            )
    except Exception:
        logger.exception("Error in scheduled crawl check")
    finally:
        await db.close()


def init_scheduler():
    """Start the periodic crawl check (every 5 minutes)."""
    scheduler.add_job(
        check_and_schedule_crawls,
        "interval",
        minutes=5,
        id="crawl_check",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Crawl scheduler started (checking every 5 minutes)")
