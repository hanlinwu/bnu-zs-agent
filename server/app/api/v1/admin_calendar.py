"""Admission calendar management API for administrators."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError, BizError
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.models.calendar import AdmissionCalendar

router = APIRouter()


class CalendarCreateRequest(BaseModel):
    period_name: str
    start_month: int
    end_month: int
    year: int
    tone_config: dict
    additional_prompt: str | None = None
    is_active: bool = True


class CalendarUpdateRequest(BaseModel):
    period_name: str | None = None
    start_month: int | None = None
    end_month: int | None = None
    year: int | None = None
    tone_config: dict | None = None
    additional_prompt: str | None = None
    is_active: bool | None = None


@router.get("", dependencies=[Depends(require_permission("calendar:read"))])
async def list_calendars(
    year: int | None = Query(None, description="按年度筛选"),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """招生日历配置列表"""
    stmt = select(AdmissionCalendar)
    if year:
        stmt = stmt.where(AdmissionCalendar.year == year)
    stmt = stmt.order_by(AdmissionCalendar.year.desc(), AdmissionCalendar.start_month)

    result = await db.execute(stmt)
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
                "additional_prompt": c.additional_prompt,
                "is_active": c.is_active,
                "updated_by": str(c.updated_by) if c.updated_by else None,
                "updated_at": c.updated_at.isoformat(),
            }
            for c in calendars
        ]
    }


@router.get("/years", dependencies=[Depends(require_permission("calendar:read"))])
async def list_years(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取所有可用的年度列表"""
    result = await db.execute(
        select(AdmissionCalendar.year).distinct().order_by(AdmissionCalendar.year.desc())
    )
    years = result.scalars().all()
    return {"years": list(years)}


@router.post("", dependencies=[Depends(require_permission("calendar:create"))])
async def create_calendar(
    body: CalendarCreateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建招生日历时段"""
    if not 1 <= body.start_month <= 12:
        raise BizError(code=400, message="start_month 必须在 1-12 之间")
    if not 1 <= body.end_month <= 12:
        raise BizError(code=400, message="end_month 必须在 1-12 之间")

    cal = AdmissionCalendar(
        period_name=body.period_name,
        start_month=body.start_month,
        end_month=body.end_month,
        year=body.year,
        tone_config=body.tone_config,
        additional_prompt=body.additional_prompt,
        is_active=body.is_active,
        updated_by=admin.id,
    )
    db.add(cal)
    await db.commit()
    await db.refresh(cal)

    return {
        "id": str(cal.id),
        "period_name": cal.period_name,
        "start_month": cal.start_month,
        "end_month": cal.end_month,
        "year": cal.year,
        "tone_config": cal.tone_config,
        "additional_prompt": cal.additional_prompt,
        "is_active": cal.is_active,
        "updated_at": cal.updated_at.isoformat(),
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
    if body.additional_prompt is not None:
        cal.additional_prompt = body.additional_prompt
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
        "additional_prompt": cal.additional_prompt,
        "is_active": cal.is_active,
        "updated_by": str(cal.updated_by),
        "updated_at": cal.updated_at.isoformat(),
    }


@router.delete("/{calendar_id}", dependencies=[Depends(require_permission("calendar:delete"))])
async def delete_calendar(
    calendar_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除招生日历时段"""
    result = await db.execute(select(AdmissionCalendar).where(AdmissionCalendar.id == calendar_id))
    cal = result.scalar_one_or_none()
    if not cal:
        raise NotFoundError("日历配置不存在")

    await db.delete(cal)
    await db.commit()

    return {"success": True, "message": "日历时段已删除"}
