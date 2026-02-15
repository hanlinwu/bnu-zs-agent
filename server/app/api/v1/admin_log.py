"""Audit log API for administrators."""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.models.audit_log import AuditLog

router = APIRouter()


@router.get("", dependencies=[Depends(require_permission("log:read"))])
async def list_audit_logs(
    action: str | None = None,
    resource: str | None = None,
    user_id: str | None = None,
    admin_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """审计日志列表（分页、多条件筛选）"""
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)

    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if resource:
        filters.append(AuditLog.resource == resource)
    if user_id:
        filters.append(AuditLog.user_id == user_id)
    if admin_id:
        filters.append(AuditLog.admin_id == admin_id)
    if start_time:
        filters.append(AuditLog.created_at >= start_time)
    if end_time:
        filters.append(AuditLog.created_at <= end_time)

    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = (
        stmt.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return {
        "items": [
            {
                "id": log.id,
                "user_id": str(log.user_id) if log.user_id else None,
                "admin_id": str(log.admin_id) if log.admin_id else None,
                "action": log.action,
                "resource": log.resource,
                "resource_id": str(log.resource_id) if log.resource_id else None,
                "ip_address": str(log.ip_address) if log.ip_address else None,
                "user_agent": log.user_agent,
                "detail": log.detail,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/export", dependencies=[Depends(require_permission("log:export"))])
async def export_audit_logs(
    action: str | None = None,
    resource: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """导出审计日志为 CSV"""
    stmt = select(AuditLog)

    if action:
        stmt = stmt.where(AuditLog.action == action)
    if resource:
        stmt = stmt.where(AuditLog.resource == resource)
    if start_time:
        stmt = stmt.where(AuditLog.created_at >= start_time)
    if end_time:
        stmt = stmt.where(AuditLog.created_at <= end_time)

    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(10000)
    result = await db.execute(stmt)
    logs = result.scalars().all()

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "用户ID", "管理员ID", "操作", "资源", "资源ID",
        "IP地址", "User-Agent", "详情", "时间",
    ])
    for log in logs:
        writer.writerow([
            log.id,
            str(log.user_id) if log.user_id else "",
            str(log.admin_id) if log.admin_id else "",
            log.action,
            log.resource or "",
            str(log.resource_id) if log.resource_id else "",
            str(log.ip_address) if log.ip_address else "",
            log.user_agent or "",
            str(log.detail) if log.detail else "",
            log.created_at.isoformat(),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )
