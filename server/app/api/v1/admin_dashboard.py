"""Dashboard statistics API for administrators."""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message

router = APIRouter()


@router.get("/stats", dependencies=[Depends(require_permission("dashboard:read"))])
async def get_stats(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """统计卡片：用户总数、对话总数、今日活跃用户数"""
    user_count = (
        await db.execute(select(func.count()).select_from(User))
    ).scalar() or 0

    conversation_count = (
        await db.execute(
            select(func.count()).select_from(Conversation).where(Conversation.is_deleted == False)
        )
    ).scalar() or 0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    active_today = (
        await db.execute(
            select(func.count(func.distinct(Conversation.user_id)))
            .select_from(Conversation)
            .where(
                Conversation.is_deleted == False,
                Conversation.updated_at >= today_start,
            )
        )
    ).scalar() or 0

    message_count = (
        await db.execute(
            select(func.count()).select_from(Message).where(Message.is_deleted == False)
        )
    ).scalar() or 0

    return {
        "user_count": user_count,
        "conversation_count": conversation_count,
        "active_today": active_today,
        "message_count": message_count,
    }


@router.get("/trends", dependencies=[Depends(require_permission("dashboard:read"))])
async def get_trends(
    days: int = Query(30, ge=1, le=90),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """对话量趋势（最近 N 天）"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(
            cast(Conversation.created_at, Date).label("date"),
            func.count().label("count"),
        )
        .where(
            Conversation.is_deleted == False,
            Conversation.created_at >= start_date,
        )
        .group_by(cast(Conversation.created_at, Date))
        .order_by(cast(Conversation.created_at, Date))
    )
    result = await db.execute(stmt)
    rows = result.all()

    return {
        "items": [
            {"date": row.date.isoformat(), "count": row.count}
            for row in rows
        ]
    }


@router.get("/hot", dependencies=[Depends(require_permission("dashboard:read"))])
async def get_hot_questions(
    limit: int = Query(20, ge=1, le=100),
    days: int = Query(7, ge=1, le=90),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """热门问题排行"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Get most frequent user messages (truncated to first 100 chars for grouping)
    stmt = (
        select(
            func.left(Message.content, 100).label("question"),
            func.count().label("count"),
        )
        .where(
            Message.role == "user",
            Message.is_deleted == False,
            Message.created_at >= start_date,
        )
        .group_by(func.left(Message.content, 100))
        .order_by(func.count().desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return {
        "items": [
            {"question": row.question, "count": row.count}
            for row in rows
        ]
    }
