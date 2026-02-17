"""Audit log storage service using daily SQLite shard files."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from app.config import settings


logger = logging.getLogger(__name__)


TABLE_SQL = """
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    admin_id TEXT,
    action TEXT NOT NULL,
    resource TEXT,
    resource_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    detail TEXT,
    created_at TEXT NOT NULL
)
"""

INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)",
    "CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource)",
    "CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_audit_admin ON audit_logs(admin_id)",
]


def _audit_dir() -> Path:
    preferred = Path(settings.AUDIT_SQLITE_DIR)
    fallback_candidates = [
        Path("/workspace/tmp/audit_logs"),
        Path.cwd() / "tmp" / "audit_logs",
        Path(tempfile.gettempdir()) / "bnu_audit_logs",
    ]

    candidates = [preferred, *fallback_candidates]
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_probe"
            with probe.open("w", encoding="utf-8") as f:
                f.write("ok")
            probe.unlink(missing_ok=True)

            if candidate != preferred:
                logger.warning(
                    "AUDIT_SQLITE_DIR '%s' is not writable, fallback to '%s'",
                    preferred,
                    candidate,
                )
            return candidate
        except Exception:
            continue

    raise RuntimeError("No writable directory available for SQLite audit logs")


def _db_path_for(dt: datetime) -> Path:
    return _audit_dir() / f"audit_{dt.strftime('%Y%m%d')}.db"


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), timeout=5, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute(TABLE_SQL)
    for sql in INDEX_SQL:
        conn.execute(sql)
    return conn


def _parse_created_at(value: str | datetime | None) -> datetime:
    if value is None:
        return datetime.utcnow()
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return datetime.utcnow()


def _iter_dates(start_time: datetime, end_time: datetime):
    current = start_time.date()
    end_date = end_time.date()
    while current <= end_date:
        yield current
        current = current + timedelta(days=1)


def _extract_date_from_filename(path: Path) -> datetime | None:
    stem = path.stem
    if not stem.startswith("audit_"):
        return None
    date_str = stem.replace("audit_", "")
    try:
        return datetime.strptime(date_str, "%Y%m%d")
    except Exception:
        return None


def _candidate_files(start_time: datetime | None, end_time: datetime | None) -> list[Path]:
    directory = _audit_dir()

    if start_time and end_time:
        files: list[Path] = []
        for d in _iter_dates(start_time, end_time):
            file = directory / f"audit_{d.strftime('%Y%m%d')}.db"
            if file.exists():
                files.append(file)
        return sorted(files, reverse=True)

    files = [p for p in directory.glob("audit_*.db") if p.is_file()]
    files.sort(key=lambda p: p.name, reverse=True)
    return files


def _build_where_clause(
    action: str | None,
    resource: str | None,
    user_id: str | None,
    admin_id: str | None,
    start_time: datetime | None,
    end_time: datetime | None,
) -> tuple[str, list]:
    conds: list[str] = []
    params: list = []

    if action:
        conds.append("action = ?")
        params.append(action)
    if resource:
        conds.append("resource = ?")
        params.append(resource)
    if user_id:
        conds.append("user_id = ?")
        params.append(user_id)
    if admin_id:
        conds.append("admin_id = ?")
        params.append(admin_id)
    if start_time:
        conds.append("created_at >= ?")
        params.append(start_time.isoformat())
    if end_time:
        conds.append("created_at <= ?")
        params.append(end_time.isoformat())

    if not conds:
        return "", params
    return "WHERE " + " AND ".join(conds), params


def _count_in_file(path: Path, where_clause: str, params: list) -> int:
    conn = _connect(path)
    try:
        sql = f"SELECT COUNT(*) AS total FROM audit_logs {where_clause}"
        row = conn.execute(sql, params).fetchone()
        return int(row["total"] if row else 0)
    finally:
        conn.close()


def _fetch_in_file(path: Path, where_clause: str, params: list, offset: int, limit: int) -> list[dict]:
    conn = _connect(path)
    try:
        sql = (
            "SELECT id, user_id, admin_id, action, resource, resource_id, "
            "ip_address, user_agent, detail, created_at "
            f"FROM audit_logs {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?"
        )
        rows = conn.execute(sql, [*params, limit, offset]).fetchall()
        items: list[dict] = []
        for row in rows:
            detail_value = None
            if row["detail"]:
                try:
                    detail_value = json.loads(row["detail"])
                except Exception:
                    detail_value = {"raw": row["detail"]}

            items.append(
                {
                    "id": int(row["id"]),
                    "user_id": row["user_id"],
                    "admin_id": row["admin_id"],
                    "action": row["action"],
                    "resource": row["resource"],
                    "resource_id": row["resource_id"],
                    "ip_address": row["ip_address"],
                    "user_agent": row["user_agent"],
                    "detail": detail_value,
                    "created_at": row["created_at"],
                }
            )
        return items
    finally:
        conn.close()


def _append_audit_log_sync(entry: dict) -> None:
    created_at = _parse_created_at(entry.get("created_at"))
    path = _db_path_for(created_at)

    conn = _connect(path)
    try:
        conn.execute(
            """
            INSERT INTO audit_logs (
                user_id, admin_id, action, resource, resource_id,
                ip_address, user_agent, detail, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.get("user_id"),
                entry.get("admin_id"),
                entry.get("action") or "query",
                entry.get("resource"),
                entry.get("resource_id"),
                entry.get("ip_address"),
                entry.get("user_agent"),
                json.dumps(entry.get("detail") or {}, ensure_ascii=False),
                created_at.isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


async def append_audit_log(entry: dict) -> None:
    await asyncio.to_thread(_append_audit_log_sync, entry)


def _list_audit_logs_sync(
    action: str | None,
    resource: str | None,
    user_id: str | None,
    admin_id: str | None,
    start_time: datetime | None,
    end_time: datetime | None,
    page: int,
    page_size: int,
) -> dict:
    files = _candidate_files(start_time, end_time)
    if not files:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}

    where_clause, params = _build_where_clause(action, resource, user_id, admin_id, start_time, end_time)

    total = 0
    counts: list[tuple[Path, int]] = []
    for file in files:
        count = _count_in_file(file, where_clause, params)
        total += count
        counts.append((file, count))

    offset_left = max(0, (page - 1) * page_size)
    remaining = page_size
    items: list[dict] = []

    for file, count in counts:
        if count <= 0:
            continue
        if offset_left >= count:
            offset_left -= count
            continue

        fetched = _fetch_in_file(file, where_clause, params, offset_left, remaining)
        items.extend(fetched)
        remaining -= len(fetched)
        offset_left = 0
        if remaining <= 0:
            break

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def list_audit_logs(
    action: str | None,
    resource: str | None,
    user_id: str | None,
    admin_id: str | None,
    start_time: datetime | None,
    end_time: datetime | None,
    page: int,
    page_size: int,
) -> dict:
    return await asyncio.to_thread(
        _list_audit_logs_sync,
        action,
        resource,
        user_id,
        admin_id,
        start_time,
        end_time,
        page,
        page_size,
    )
