"""Audit log API for administrators."""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.services.audit_sqlite_service import list_audit_logs as list_audit_logs_from_sqlite

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
):
    """审计日志列表（分页、多条件筛选）"""
    return await list_audit_logs_from_sqlite(
        action=action,
        resource=resource,
        user_id=user_id,
        admin_id=admin_id,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )


@router.get("/export", dependencies=[Depends(require_permission("log:export"))])
async def export_audit_logs(
    action: str | None = None,
    resource: str | None = None,
    user_id: str | None = None,
    admin_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    admin: AdminUser = Depends(get_current_admin),
):
    """导出审计日志为 CSV"""
    result = await list_audit_logs_from_sqlite(
        action=action,
        resource=resource,
        user_id=user_id,
        admin_id=admin_id,
        start_time=start_time,
        end_time=end_time,
        page=1,
        page_size=10000,
    )
    logs = result.get("items", [])

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "用户ID", "管理员ID", "操作", "资源", "资源ID",
        "IP地址", "User-Agent", "详情", "时间",
    ])
    for log in logs:
        writer.writerow([
            log.get("id", ""),
            log.get("user_id") or "",
            log.get("admin_id") or "",
            log.get("action") or "",
            log.get("resource") or "",
            log.get("resource_id") or "",
            log.get("ip_address") or "",
            log.get("user_agent") or "",
            str(log.get("detail")) if log.get("detail") else "",
            log.get("created_at") or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )
