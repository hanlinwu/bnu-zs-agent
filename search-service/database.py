"""SQLite database for crawl sites and task history."""

import os
import aiosqlite
from config import settings

_DB_PATH = settings.SQLITE_DB_PATH

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS crawl_sites (
    id          TEXT PRIMARY KEY,
    domain      TEXT NOT NULL UNIQUE,
    name        TEXT,
    start_url   TEXT NOT NULL,
    max_depth   INTEGER NOT NULL DEFAULT 3,
    max_pages   INTEGER NOT NULL DEFAULT 100,
    same_domain_only INTEGER NOT NULL DEFAULT 1,
    crawl_frequency_minutes INTEGER NOT NULL DEFAULT 1440,
    enabled     INTEGER NOT NULL DEFAULT 1,
    last_crawl_at TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crawl_tasks (
    id            TEXT PRIMARY KEY,
    site_id       TEXT,
    start_url     TEXT NOT NULL,
    max_depth     INTEGER NOT NULL DEFAULT 3,
    max_pages     INTEGER NOT NULL DEFAULT 100,
    same_domain_only INTEGER NOT NULL DEFAULT 1,
    status        TEXT NOT NULL DEFAULT 'pending',
    progress      INTEGER NOT NULL DEFAULT 0,
    total_pages   INTEGER NOT NULL DEFAULT 0,
    success_pages INTEGER NOT NULL DEFAULT 0,
    failed_pages  INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at    TEXT,
    finished_at   TEXT,
    created_at    TEXT NOT NULL,
    FOREIGN KEY (site_id) REFERENCES crawl_sites(id) ON DELETE SET NULL
);
"""


async def init_db():
    """Create tables if they don't exist."""
    os.makedirs(os.path.dirname(_DB_PATH) or ".", exist_ok=True)
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.executescript(CREATE_TABLES_SQL)
        await db.commit()


async def get_db() -> aiosqlite.Connection:
    """Return an open connection (caller must close or use as context manager)."""
    db = await aiosqlite.connect(_DB_PATH)
    db.row_factory = aiosqlite.Row
    return db
