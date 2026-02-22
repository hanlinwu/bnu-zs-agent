"""Conversation history management routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.dependencies import get_current_user
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.chat import (
    ConversationCreate, ConversationUpdate, ConversationResponse,
    ConversationListResponse, MessageResponse, MessageListResponse,
)

router = APIRouter()


def _split_sources_payload(raw_sources):
    if isinstance(raw_sources, dict):
        citations = raw_sources.get("citations")
        media_items = raw_sources.get("media_items")
        tools_used = raw_sources.get("tools_used")
        tool_traces = raw_sources.get("tool_traces")
        if citations is None:
            citations = []
        if media_items is None:
            media_items = []
        if tools_used is None:
            tools_used = []
        if tool_traces is None:
            tool_traces = []
        return citations or None, media_items or None, tools_used or None, tool_traces or None

    if isinstance(raw_sources, list):
        return raw_sources or None, None, None, None

    return None, None, None, None


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """对话列表（分页，排除软删除）"""
    base_filter = and_(
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False,
    )

    # Count
    count_stmt = select(func.count()).select_from(Conversation).where(base_filter)
    total = (await db.execute(count_stmt)).scalar() or 0

    # Query with message count
    msg_count = (
        select(func.count())
        .select_from(Message)
        .where(and_(Message.conversation_id == Conversation.id, Message.is_deleted == False))
        .correlate(Conversation)
        .scalar_subquery()
    )

    stmt = (
        select(Conversation, msg_count.label("message_count"))
        .where(base_filter)
        .order_by(Conversation.is_pinned.desc(), Conversation.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    rows = result.all()

    items = [
        ConversationResponse(
            id=str(conv.id),
            title=conv.title,
            is_pinned=conv.is_pinned,
            created_at=conv.created_at.isoformat(),
            updated_at=conv.updated_at.isoformat(),
            message_count=msg_count_val or 0,
        )
        for conv, msg_count_val in rows
    ]

    return ConversationListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    body: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """新建对话"""
    conv = Conversation(
        user_id=current_user.id,
        title=body.title,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)

    return ConversationResponse(
        id=str(conv.id),
        title=conv.title,
        is_pinned=conv.is_pinned,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
    )


@router.get("/{conv_id}", response_model=ConversationResponse)
async def get_conversation(
    conv_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """对话详情"""
    conv = await _get_user_conversation(conv_id, current_user.id, db)

    msg_count_stmt = select(func.count()).select_from(Message).where(
        and_(Message.conversation_id == conv.id, Message.is_deleted == False)
    )
    msg_count = (await db.execute(msg_count_stmt)).scalar() or 0

    return ConversationResponse(
        id=str(conv.id),
        title=conv.title,
        is_pinned=conv.is_pinned,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
        message_count=msg_count,
    )


@router.put("/{conv_id}", response_model=ConversationResponse)
async def update_conversation(
    conv_id: str,
    body: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新标题/置顶"""
    conv = await _get_user_conversation(conv_id, current_user.id, db)

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(conv, key, value)
    conv.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(conv)

    return ConversationResponse(
        id=str(conv.id),
        title=conv.title,
        is_pinned=conv.is_pinned,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
    )


@router.delete("/{conv_id}")
async def delete_conversation(
    conv_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """软删除对话"""
    conv = await _get_user_conversation(conv_id, current_user.id, db)
    conv.is_deleted = True
    conv.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True, "message": "对话已删除"}


@router.get("/{conv_id}/messages", response_model=MessageListResponse)
async def list_messages(
    conv_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    before: str | None = Query(None, description="加载此ID之前的消息（更早的消息）"),
    after: str | None = Query(None, description="加载此ID之后的消息（更新的消息）"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """消息列表（分页）- 支持游标分页优化聊天历史加载

    常规分页: page + page_size
    游标分页: before 或 after + page_size（用于无限滚动）
    """
    conv = await _get_user_conversation(conv_id, current_user.id, db)

    base_filter = and_(
        Message.conversation_id == conv.id,
        Message.is_deleted == False,
    )

    # 获取总数（用于首次加载显示）
    count_stmt = select(func.count()).select_from(Message).where(base_filter)
    total = (await db.execute(count_stmt)).scalar() or 0

    # 游标分页逻辑
    if before:
        # 加载更早的消息（向上滚动）
        # 先获取游标消息（时间+ID 作为联合游标，避免同时间戳乱序/漏数）
        cursor_msg = await db.execute(
            select(Message).where(and_(
                Message.id == before,
                Message.conversation_id == conv.id,
                Message.is_deleted == False,
            ))
        )
        cursor_msg = cursor_msg.scalar_one_or_none()
        if cursor_msg:
            stmt = (
                select(Message)
                .where(and_(
                    base_filter,
                    or_(
                        Message.created_at < cursor_msg.created_at,
                        and_(
                            Message.created_at == cursor_msg.created_at,
                            Message.id < cursor_msg.id,
                        ),
                    ),
                ))
                .order_by(Message.created_at.desc(), Message.id.desc())  # 降序取最新的旧消息
                .limit(page_size)
            )
            result = await db.execute(stmt)
            messages = result.scalars().all()
            # 反转为正序（从早到晚）
            messages = list(reversed(messages))
        else:
            messages = []
    elif after:
        # 加载更新的消息（向下滚动/新消息）
        cursor_msg = await db.execute(
            select(Message).where(and_(
                Message.id == after,
                Message.conversation_id == conv.id,
                Message.is_deleted == False,
            ))
        )
        cursor_msg = cursor_msg.scalar_one_or_none()
        if cursor_msg:
            stmt = (
                select(Message)
                .where(and_(
                    base_filter,
                    or_(
                        Message.created_at > cursor_msg.created_at,
                        and_(
                            Message.created_at == cursor_msg.created_at,
                            Message.id > cursor_msg.id,
                        ),
                    ),
                ))
                .order_by(Message.created_at.asc(), Message.id.asc())
                .limit(page_size)
            )
            result = await db.execute(stmt)
            messages = result.scalars().all()
        else:
            messages = []
    else:
        # 常规分页或首次加载（默认加载最新的消息）
        # 计算偏移：从最新的消息开始
        offset = (page - 1) * page_size
        # 先按时间降序获取，再反转成正序
        stmt = (
            select(Message)
            .where(base_filter)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        messages = result.scalars().all()
        # 反转为正序（从早到晚显示）
        messages = list(reversed(messages))

    # 确保稳定正序（从早到晚，同时间戳按 ID）
    sorted_messages = sorted(messages, key=lambda m: (m.created_at, m.id))

    items = []
    for m in sorted_messages:
        citations, media_items, tools_used, tool_traces = _split_sources_payload(m.sources)
        items.append(
            MessageResponse(
                id=str(m.id),
                role=m.role,
                content=m.content,
                model_version=m.model_version,
                risk_level=m.risk_level,
                review_passed=m.review_passed,
                sources=citations,
                media_items=media_items,
                tools_used=tools_used,
                tool_traces=tool_traces,
                created_at=m.created_at.isoformat(),
            )
        )

    return MessageListResponse(items=items, total=total, page=page, page_size=page_size)


async def _get_user_conversation(conv_id: str, user_id, db: AsyncSession) -> Conversation:
    """Get a conversation owned by the user, or raise 404."""
    result = await db.execute(
        select(Conversation).where(
            and_(
                Conversation.id == conv_id,
                Conversation.user_id == user_id,
                Conversation.is_deleted == False,
            )
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise NotFoundError("对话不存在")
    return conv
