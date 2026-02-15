"""Admission calendar management API for administrators."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError, BizError
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.models.calendar import AdmissionCalendar

router = APIRouter()


class CalendarUpdateRequest(BaseModel):
    period_name: str | None = None
    start_month: int | None = None
    end_month: int | None = None
    year: int | None = None
    tone_config: dict | None = None
    is_active: bool | None = None


@router.get("", dependencies=[Depends(require_permission("calendar:read"))])
async def list_calendars(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """招生日历配置列表"""
    result = await db.execute(
        select(AdmissionCalendar).order_by(AdmissionCalendar.year.desc(), AdmissionCalendar.start_month)
    )
    calendars = result.scalars().all()

    return {
        "items": [
            {
                "id": str(c.id),
                "period_name": c.period_name,
                "start_month": c.start_month,
                "end_month": c.end_month,
                "year": c.year,
                "tone_config": c.tone_config,
                "is_active": c.is_active,
                "updated_by": str(c.updated_by) if c.updated_by else None,
                "updated_at": c.updated_at.isoformat(),
            }
            for c in calendars
        ]
    }


@router.put("/{calendar_id}", dependencies=[Depends(require_permission("calendar:update"))])
async def update_calendar(
    calendar_id: str,
    body: CalendarUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新招生日历时段配置"""
    result = await db.execute(select(AdmissionCalendar).where(AdmissionCalendar.id == calendar_id))
    cal = result.scalar_one_or_none()
    if not cal:
        raise NotFoundError("日历配置不存在")

    if body.period_name is not None:
        cal.period_name = body.period_name
    if body.start_month is not None:
        if not 1 <= body.start_month <= 12:
            raise BizError(code=400, message="start_month 必须在 1-12 之间")
        cal.start_month = body.start_month
    if body.end_month is not None:
        if not 1 <= body.end_month <= 12:
            raise BizError(code=400, message="end_month 必须在 1-12 之间")
        cal.end_month = body.end_month
    if body.year is not None:
        cal.year = body.year
    if body.tone_config is not None:
        cal.tone_config = body.tone_config
    if body.is_active is not None:
        cal.is_active = body.is_active

    cal.updated_by = admin.id
    cal.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(cal)

    return {
        "id": str(cal.id),
        "period_name": cal.period_name,
        "start_month": cal.start_month,
        "end_month": cal.end_month,
        "year": cal.year,
        "tone_config": cal.tone_config,
        "is_active": cal.is_active,
        "updated_by": str(cal.updated_by),
        "updated_at": cal.updated_at.isoformat(),
    }
