"""Conversation audit API for administrators."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case, and_, exists
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.permissions import require_permission
from app.dependencies import get_current_admin
from app.models.admin import AdminUser
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User

router = APIRouter()

RISK_ORDER = case(
    (Message.risk_level == "blocked", 4),
    (Message.risk_level == "high", 3),
    (Message.risk_level == "medium", 2),
    (Message.risk_level == "low", 1),
    else_=0,
)

RISK_LABELS = {4: "blocked", 3: "high", 2: "medium", 1: "low", 0: None}

SENSITIVE_ORDER = case(
    (Message.sensitive_level == "block", 3),
    (Message.sensitive_level == "review", 2),
    (Message.sensitive_level == "warn", 1),
    else_=0,
)

SENSITIVE_LABELS = {3: "block", 2: "review", 1: "warn", 0: None}


@router.get("", dependencies=[Depends(require_permission("conversation:read"))])
async def list_conversations(
    keyword: str | None = None,
    risk_level: str | None = None,
    sensitive_level: str | None = None,
    include_deleted: bool = Query(True, description="是否包含用户侧已删除对话"),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """对话列表（分页、筛选、聚合统计）"""

    # Message stats subquery
    msg_stats = (
        select(
            Message.conversation_id,
            func.count(Message.id).label("message_count"),
            func.coalesce(
                func.sum(case((Message.role == "user", func.length(Message.content)), else_=0)), 0
            ).label("user_char_count"),
            func.coalesce(
                func.sum(case((Message.role == "assistant", func.length(Message.content)), else_=0)), 0
            ).label("assistant_char_count"),
            func.max(RISK_ORDER).label("risk_order"),
            func.max(SENSITIVE_ORDER).label("sensitive_order"),
        )
        .where(Message.is_deleted == False)
        .group_by(Message.conversation_id)
        .subquery()
    )

    # Base query: join conversation + user + stats
    base_filter = []
    if not include_deleted:
        base_filter.append(Conversation.is_deleted == False)

    if keyword:
        like_pattern = f"%{keyword}%"
        base_filter.append(
            (User.nickname.ilike(like_pattern)) | (User.phone.like(like_pattern))
        )

    if start_time:
        base_filter.append(Conversation.created_at >= start_time)
    if end_time:
        base_filter.append(Conversation.created_at <= end_time)

    if risk_level:
        base_filter.append(
            exists(
                select(Message.id).where(
                    and_(
                        Message.conversation_id == Conversation.id,
                        Message.is_deleted == False,
                        Message.risk_level == risk_level,
                    )
                )
            )
        )

    if sensitive_level:
        base_filter.append(
            exists(
                select(Message.id).where(
                    and_(
                        Message.conversation_id == Conversation.id,
                        Message.is_deleted == False,
                        Message.sensitive_level == sensitive_level,
                    )
                )
            )
        )

    # Count query
    count_stmt = (
        select(func.count())
        .select_from(Conversation)
        .join(User, User.id == Conversation.user_id)
        .where(*base_filter)
    )
    total = (await db.execute(count_stmt)).scalar() or 0

    # Data query
    stmt = (
        select(
            Conversation.id,
            Conversation.user_id,
            User.phone.label("user_phone"),
            User.nickname.label("user_nickname"),
            Conversation.title,
            Conversation.is_deleted,
            Conversation.deleted_at,
            func.coalesce(msg_stats.c.message_count, 0).label("message_count"),
            func.coalesce(msg_stats.c.user_char_count, 0).label("user_char_count"),
            func.coalesce(msg_stats.c.assistant_char_count, 0).label("assistant_char_count"),
            msg_stats.c.risk_order,
            msg_stats.c.sensitive_order,
            Conversation.created_at,
            Conversation.updated_at,
        )
        .join(User, User.id == Conversation.user_id)
        .outerjoin(msg_stats, msg_stats.c.conversation_id == Conversation.id)
        .where(*base_filter)
        .order_by(Conversation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return {
        "items": [
            {
                "id": str(row.id),
                "user_id": str(row.user_id),
                "user_phone": row.user_phone,
                "user_nickname": row.user_nickname,
                "title": row.title,
                "message_count": row.message_count,
                "user_char_count": row.user_char_count,
                "assistant_char_count": row.assistant_char_count,
                "max_risk_level": RISK_LABELS.get(row.risk_order or 0),
                "max_sensitive_level": SENSITIVE_LABELS.get(row.sensitive_order or 0),
                "is_deleted": bool(row.is_deleted),
                "deleted_at": row.deleted_at.isoformat() if row.deleted_at else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/{conversation_id}/messages",
    dependencies=[Depends(require_permission("conversation:read"))],
)
async def get_conversation_messages(
    conversation_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取对话的所有消息详情"""
    # Verify conversation exists
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = conv_result.scalar_one_or_none()
    if not conv:
        raise NotFoundError("对话不存在")

    # Fetch messages
    msg_result = await db.execute(
        select(Message)
        .where(
            and_(
                Message.conversation_id == conversation_id,
                Message.is_deleted == False,
            )
        )
        .order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    return {
        "conversation_id": str(conv.id),
        "title": conv.title,
        "messages": [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "char_count": len(msg.content) if msg.content else 0,
                "risk_level": msg.risk_level,
                "review_passed": msg.review_passed,
                "sources": msg.sources,
                "sensitive_words": msg.sensitive_words,
                "sensitive_level": msg.sensitive_level,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in messages
        ],
    }
