"""Chat routes — WebSocket streaming and HTTP fallback."""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db, get_session_factory
from app.core.security import verify_token
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.role import UserRole, Role
from app.schemas.chat import ChatSendRequest, MessageResponse
from app.dependencies import get_current_user
from app.services.chat_service import process_message

logger = logging.getLogger(__name__)

router = APIRouter()

# Active streaming sessions: conversation_id -> cancel_event
_active_streams: dict[str, asyncio.Event] = {}


async def _save_partial_response(
    conversation_id: str,
    content: str,
    user_message: str,
    risk_level: str = "low",
) -> None:
    """Save partial response to DB using a fresh session (fire-and-forget)."""
    try:
        session_factory = get_session_factory()
        async with session_factory() as db:
            # Save user message
            db.add(Message(
                conversation_id=conversation_id,
                role="user",
                content=user_message,
                risk_level=risk_level,
            ))
            # Save partial assistant response
            db.add(Message(
                conversation_id=conversation_id,
                role="assistant",
                content=content if content else "（已停止生成）",
                risk_level=risk_level,
                review_passed=True,
            ))
            await db.commit()
            logger.info("Saved partial response (%d chars) for conversation %s",
                        len(content), conversation_id)
    except Exception as e:
        logger.error("Failed to save partial response: %s", e)


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
    request: Request,
    conversation_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE streaming chat endpoint with stop support."""
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

    cancel_event = asyncio.Event()
    conv_id_str = str(conv.id)
    _active_streams[conv_id_str] = cancel_event

    # Track partial tokens for background save on stop
    partial_tokens: list[str] = []

    async def event_generator():
        try:
            async for event in process_message(
                current_user, conv, body.content, user_role, db,
                cancel_event=cancel_event,
            ):
                if event.get("type") == "token":
                    partial_tokens.append(event["content"])

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                # Check if cancelled (set by /stop endpoint)
                if cancel_event.is_set():
                    break

            yield "data: [DONE]\n\n"
        finally:
            _active_streams.pop(conv_id_str, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/stop")
async def stop_generation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
):
    """Stop an active streaming response and save partial content to DB."""
    cancel_event = _active_streams.get(conversation_id)
    if cancel_event:
        cancel_event.set()
        return {"success": True, "message": "已停止生成"}
    return {"success": False, "message": "没有活跃的生成任务"}
