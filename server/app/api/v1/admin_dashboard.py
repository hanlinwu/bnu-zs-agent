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
from app.models.knowledge import KnowledgeDocument
from app.models.media import MediaResource
from app.models.admin import AdminUser as AdminModel

router = APIRouter()


@router.get("/stats", dependencies=[Depends(require_permission("dashboard:read"))])
async def get_stats(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """统计卡片：用户/对话/消息/知识库/媒体等核心运营指标。"""
    user_count = (
        await db.execute(select(func.count()).select_from(User))
    ).scalar() or 0

    admin_count = (
        await db.execute(select(func.count()).select_from(AdminModel).where(AdminModel.status == "active"))
    ).scalar() or 0

    conversation_count = (
        await db.execute(
            select(func.count()).select_from(Conversation).where(Conversation.is_deleted == False)
        )
    ).scalar() or 0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

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

    active_7d = (
        await db.execute(
            select(func.count(func.distinct(Conversation.user_id)))
            .select_from(Conversation)
            .where(
                Conversation.is_deleted == False,
                Conversation.updated_at >= week_start,
            )
        )
    ).scalar() or 0

    message_count = (
        await db.execute(
            select(func.count()).select_from(Message).where(Message.is_deleted == False)
        )
    ).scalar() or 0

    message_today = (
        await db.execute(
            select(func.count())
            .select_from(Message)
            .where(
                Message.is_deleted == False,
                Message.created_at >= today_start,
            )
        )
    ).scalar() or 0

    new_user_7d = (
        await db.execute(
            select(func.count())
            .select_from(User)
            .where(User.created_at >= week_start)
        )
    ).scalar() or 0

    knowledge_count = (
        await db.execute(
            select(func.count()).select_from(KnowledgeDocument)
        )
    ).scalar() or 0

    knowledge_approved_count = (
        await db.execute(
            select(func.count())
            .select_from(KnowledgeDocument)
            .where(KnowledgeDocument.status == "approved")
        )
    ).scalar() or 0

    pending_review_count = (
        await db.execute(
            select(func.count())
            .select_from(KnowledgeDocument)
            .where(KnowledgeDocument.status == "pending")
        )
    ).scalar() or 0

    media_count = (
        await db.execute(
            select(func.count()).select_from(MediaResource)
        )
    ).scalar() or 0

    media_pending_review_count = (
        await db.execute(
            select(func.count())
            .select_from(MediaResource)
            .where(MediaResource.status == "pending")
        )
    ).scalar() or 0

    return {
        "user_count": user_count,
        "admin_count": admin_count,
        "conversation_count": conversation_count,
        "active_today": active_today,
        "active_7d": active_7d,
        "message_count": message_count,
        "message_today": message_today,
        "new_user_7d": new_user_7d,
        "knowledge_count": knowledge_count,
        "knowledge_approved_count": knowledge_approved_count,
        "pending_review_count": pending_review_count,
        "media_count": media_count,
        "media_pending_review_count": media_pending_review_count,
    }


@router.get("/trends", dependencies=[Depends(require_permission("dashboard:read"))])
async def get_trends(
    days: int = Query(30, ge=1, le=90),
    timezone_offset: int = Query(8, ge=-12, le=14, description="时区偏移，默认东八区(北京时间)"),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """对话量趋势（最近 N 天，包含无数据的日期补零，支持时区偏移）"""
    from sqlalchemy import text

    # Use SQL to convert UTC to local timezone for grouping
    # PostgreSQL: (created_at + interval 'hours')::date
    offset_hours = timezone_offset
    stmt = text(f"""
        SELECT
            DATE(created_at + INTERVAL '{offset_hours} hours') AS date,
            COUNT(*) AS count
        FROM conversations
        WHERE is_deleted = FALSE
          AND created_at >= NOW() AT TIME ZONE 'UTC' - INTERVAL '{days} days'
        GROUP BY DATE(created_at + INTERVAL '{offset_hours} hours')
        ORDER BY date
    """)

    result = await db.execute(stmt)
    rows = result.all()

    # Build a dict of existing data
    data_map = {row.date: row.count for row in rows}

    # Generate complete date sequence
    now = datetime.now(timezone.utc) + timedelta(hours=offset_hours)
    items = []
    for i in range(days - 1, -1, -1):
        date_obj = (now - timedelta(days=i)).date()
        items.append({
            "date": date_obj.isoformat(),
            "count": data_map.get(date_obj, 0),
        })

    return {"items": items}


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
    truncated = func.left(Message.content, 100).label("question")
    stmt = (
        select(
            truncated,
            func.count().label("count"),
        )
        .where(
            Message.role == "user",
            Message.is_deleted == False,
            Message.created_at >= start_date,
        )
        .group_by(truncated)
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
