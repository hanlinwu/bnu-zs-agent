"""Chat routes — WebSocket streaming and HTTP fallback."""

import json
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db, get_session_factory
from app.core.security import verify_token
from app.models.user import User
from app.models.conversation import Conversation
from app.models.role import UserRole, Role
from app.schemas.chat import ChatSendRequest, MessageResponse
from app.dependencies import get_current_user
from app.services.chat_service import process_message

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/{conversation_id}")
async def ws_chat(websocket: WebSocket, conversation_id: str):
    """WebSocket endpoint for streaming chat.

    Client sends: {"content": "user message", "token": "jwt_token"}
    Server sends: {"type": "token", "content": "..."} (streaming)
                  {"type": "done", "sources": [...]} (completion)
                  {"type": "error", "content": "..."} (error)
    """
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            token = data.get("token", "")
            content = data.get("content", "")

            if not content:
                await websocket.send_json({"type": "error", "content": "消息不能为空"})
                continue

            # Verify token
            try:
                payload = verify_token(token)
                user_id = payload["sub"]
            except Exception:
                await websocket.send_json({"type": "error", "content": "认证失败"})
                continue

            # Get DB session
            session_factory = get_session_factory()
            async with session_factory() as db:
                # Get user
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if not user or user.status != "active":
                    await websocket.send_json({"type": "error", "content": "用户无效"})
                    continue

                # Get conversation
                result = await db.execute(
                    select(Conversation).where(
                        and_(
                            Conversation.id == conversation_id,
                            Conversation.user_id == user.id,
                            Conversation.is_deleted == False,
                        )
                    )
                )
                conversation = result.scalar_one_or_none()
                if not conversation:
                    await websocket.send_json({"type": "error", "content": "对话不存在"})
                    continue

                # Get user role
                role_result = await db.execute(
                    select(Role.code)
                    .join(UserRole, UserRole.role_id == Role.id)
                    .where(UserRole.user_id == user.id)
                    .limit(1)
                )
                user_role = role_result.scalar_one_or_none()

                # Process through pipeline
                async for event in process_message(user, conversation, content, user_role, db):
                    await websocket.send_json(event)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for conversation %s", conversation_id)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        try:
            await websocket.send_json({"type": "error", "content": "服务器内部错误"})
        except Exception:
            pass


@router.post("/send")
async def send_message(
    body: ChatSendRequest,
    conversation_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE streaming chat endpoint."""
    # Create conversation if not specified
    if not conversation_id:
        conv = Conversation(user_id=current_user.id)
        db.add(conv)
        await db.flush()
        # Re-fetch with messages eagerly loaded
        result = await db.execute(
            select(Conversation).where(Conversation.id == conv.id)
            .options(selectinload(Conversation.messages))
        )
        conv = result.scalar_one()
    else:
        result = await db.execute(
            select(Conversation).where(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == current_user.id,
                    Conversation.is_deleted == False,
                )
            ).options(selectinload(Conversation.messages))
        )
        conv = result.scalar_one_or_none()
        if not conv:
            from app.core.exceptions import NotFoundError
            raise NotFoundError("对话不存在")

    # Get user role
    role_result = await db.execute(
        select(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == current_user.id)
        .limit(1)
    )
    user_role = role_result.scalar_one_or_none()

    async def event_generator():
        async for event in process_message(current_user, conv, body.content, user_role, db):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
