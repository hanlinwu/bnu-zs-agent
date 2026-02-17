"""Core chat orchestration service — the 9-step pipeline."""

import asyncio
import logging
import re
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.sensitive_service import check_sensitive
from app.services.risk_service import classify_risk
from app.services.emotion_service import detect_emotion
from app.services.calendar_service import get_current_tone
from app.services.knowledge_service import search as knowledge_search, format_sources_for_prompt, format_sources_for_citation
from app.services.system_config_service import get_chat_guardrail_config
from app.services.llm_service import llm_router
from app.services.media_match_service import match_media_for_question

logger = logging.getLogger(__name__)
MEDIA_SLOT_TOKEN = "[[MEDIA_SLOT]]"
MEDIA_SLOT_REGEX = re.compile(r"\[\[\s*MEDIA_(?:SLOT|SOLT)\s*\]\]", re.IGNORECASE)
MEDIA_TAGGED_SLOT_REGEX = re.compile(r"\[\[\s*MEDIA_(?:SLOT|SOLT)\s*:\s*([^\]]+?)\s*\]\]", re.IGNORECASE)
MEDIA_INLINE_MARKER_REGEX = re.compile(r"\[\[\s*MEDIA_ITEM:([^\]]+)\s*\]\]")


def _fill_media_slot(text: str, media_items: list[dict]) -> str:
    input_text = text or ""
    if not input_text:
        return input_text

    if media_items:
        replacement = "\n\n以下为你整理了相关校园图像/视频资料："
        output = MEDIA_SLOT_REGEX.sub(replacement, input_text)
        if output == input_text and MEDIA_SLOT_TOKEN not in input_text:
            return input_text + replacement
        return output.replace(MEDIA_SLOT_TOKEN, replacement)

    output = MEDIA_SLOT_REGEX.sub("", input_text)
    return output.replace(MEDIA_SLOT_TOKEN, "")


def _parse_slot_tags(tag_text: str) -> list[str]:
    raw = (tag_text or "").strip()
    if not raw:
        return []
    tags = [part.strip() for part in re.split(r"[,，、|/\\]+", raw) if part.strip()]
    uniq: list[str] = []
    for tag in tags:
        if tag not in uniq:
            uniq.append(tag)
    return uniq[:6]


async def _resolve_media_slots(
    response_text: str,
    user_message: str,
    db: AsyncSession,
) -> tuple[str, list[dict]]:
    text = response_text or ""
    media_items: list[dict] = []
    used_ids: set[str] = set()

    matches = list(MEDIA_TAGGED_SLOT_REGEX.finditer(text))

    if matches:
        cursor = 0
        chunks: list[str] = []
        for idx, match in enumerate(matches):
            chunks.append(text[cursor:match.start()])
            slot_tags = _parse_slot_tags(match.group(1) or "")
            candidates = await match_media_for_question(
                user_message,
                db,
                limit=1,
                preferred_tags=slot_tags,
                exclude_ids=used_ids,
            )
            if candidates:
                chosen = dict(candidates[0])
                slot_key = f"slot_{idx}"
                chosen["slot_key"] = slot_key
                chosen["slot_tags"] = slot_tags
                media_items.append(chosen)
                used_ids.add(chosen["id"])
                chunks.append(f"[[MEDIA_ITEM:{slot_key}]]")
            cursor = match.end()
        chunks.append(text[cursor:])
        text = "".join(chunks)

    # Backward compatibility: replace untagged slot tokens in-place
    untagged_matches = list(MEDIA_SLOT_REGEX.finditer(text))
    if untagged_matches:
        cursor = 0
        chunks: list[str] = []
        start_idx = len(media_items)
        for idx, match in enumerate(untagged_matches):
            chunks.append(text[cursor:match.start()])
            candidates = await match_media_for_question(
                user_message,
                db,
                limit=1,
                exclude_ids=used_ids,
            )
            if candidates:
                chosen = dict(candidates[0])
                slot_key = f"slot_{start_idx + idx}"
                chosen["slot_key"] = slot_key
                chosen["slot_tags"] = []
                media_items.append(chosen)
                used_ids.add(chosen["id"])
                chunks.append(f"[[MEDIA_ITEM:{slot_key}]]")
            cursor = match.end()
        chunks.append(text[cursor:])
        text = "".join(chunks)

    # Remove unresolved markers and noisy leftovers
    text = MEDIA_TAGGED_SLOT_REGEX.sub("", text)
    text = MEDIA_SLOT_REGEX.sub("", text)

    return text, media_items

# Role-specific system prompt fragments
ROLE_PROMPTS = {
    "gaokao": "用户是一名高考考生。请用鼓励、平易近人的口吻回答，侧重本科招生信息。",
    "kaoyan": "用户是一名考研学生。请用专业、详细的口吻回答，侧重研究生招生和学术方向。",
    "international": "用户是一名国际学生。请用清晰、友好的口吻回答，如有需要可用中英双语，侧重国际招生政策和留学生支持。",
    "parent": "用户是一名考生家长。请用耐心、温和、详细的口吻回答，侧重家长关心的就业前景、校园安全和学费。",
}

async def process_message(
    user: User,
    conversation: Conversation,
    user_message: str,
    user_role: str | None,
    db: AsyncSession,
    cancel_event: asyncio.Event | None = None,
) -> AsyncGenerator[dict, None]:
    """Process a user message through the full pipeline, yielding streaming events.

    Yields dicts with type:
    - {"type": "sensitive_block", "content": str} — message blocked
    - {"type": "high_risk", "content": str} — high risk redirect
    - {"type": "token", "content": str} — streaming token
    - {"type": "done", "sources": list, "risk_level": str, "review_passed": bool}
    """

    # Step 1: Sensitive word pre-filter
    filter_result = await check_sensitive(user_message, db)
    sensitive_level = filter_result.highest_level if filter_result.matched_words else None

    if filter_result.action == "block":
        # Save blocked message
        msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=user_message,
            risk_level="blocked",
            sensitive_words=filter_result.matched_words,
            sensitive_level=sensitive_level,
        )
        db.add(msg)
        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=filter_result.message,
            model_version="system",
            risk_level="blocked",
        )
        db.add(assistant_msg)
        await db.commit()
        yield {"type": "sensitive_block", "content": filter_result.message}
        return

    # Step 2: Risk classification
    guardrail_config = await get_chat_guardrail_config(db)
    prompts_cfg = guardrail_config.get("prompts", {})

    high_risk_response = prompts_cfg.get("high_risk_response", "")
    no_knowledge_response = prompts_cfg.get("no_knowledge_response", "")
    medium_system_prompt = prompts_cfg.get("medium_system_prompt", "")
    low_system_prompt = prompts_cfg.get("low_system_prompt", "")
    medium_citation_hint_cfg = prompts_cfg.get("medium_citation_hint", "")
    medium_knowledge_instructions = prompts_cfg.get("medium_knowledge_instructions", "")

    risk_level = classify_risk(user_message, config=guardrail_config)

    if risk_level == "high":
        msg = Message(conversation_id=conversation.id, role="user", content=user_message, risk_level="high")
        db.add(msg)
        assistant_msg = Message(
            conversation_id=conversation.id, role="assistant",
            content=high_risk_response, model_version="system", risk_level="high",
        )
        db.add(assistant_msg)
        await db.commit()
        yield {"type": "high_risk", "content": high_risk_response}
        return

    # Step 3: Time-aware tone injection
    tone_config = await get_current_tone(db)
    tone_hint = tone_config.get("system_hint", "")

    # Step 4: Emotion detection
    emotion = detect_emotion(user_message)
    emotion_hint = ""
    if emotion.comfort_prefix:
        emotion_hint = f"\n用户可能感到{emotion.emotion}，请在回答开头适当加入安慰和鼓励。"

    # Step 5: Risk-driven knowledge retrieval
    search_results = []
    knowledge_context = ""
    sources_citation = []
    if risk_level == "medium":
        search_results = await knowledge_search(
            user_message,
            db,
            top_k=5,
            recall_k=30,
            min_vector_score=0.18,
            min_hybrid_score=0.22,
        )
        knowledge_context = format_sources_for_prompt(search_results)
        sources_citation = format_sources_for_citation(search_results)

        # 中风险：无有效来源时不进入自由生成
        if not search_results:
            user_msg = Message(
                conversation_id=conversation.id,
                role="user",
                content=user_message,
                risk_level=risk_level,
                sensitive_words=filter_result.matched_words if filter_result.matched_words else None,
                sensitive_level=sensitive_level,
            )
            db.add(user_msg)

            assistant_msg = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=no_knowledge_response,
                model_version="system",
                risk_level=risk_level,
                review_passed=True,
                sources=None,
            )
            db.add(assistant_msg)
            await db.commit()

            yield {"type": "token", "content": no_knowledge_response}
            yield {
                "type": "done",
                "sources": [],
                "risk_level": risk_level,
                "review_passed": True,
            }
            return

    # Step 6: Prompt assembly
    role_hint = ROLE_PROMPTS.get(user_role or "", "")
    citation_hint = ""
    if risk_level == "medium":
        citation_hint = f"\n{medium_citation_hint_cfg}" if medium_citation_hint_cfg else ""

    base_prompt = medium_system_prompt if risk_level == "medium" else low_system_prompt
    media_slot_hint = (
        f"\n\n如果用户问题涉及校园环境、校园生活、宿舍、食堂、图书馆、教学设施，"
        f"或用户明确希望查看图片/视频，请在回答中单独输出占位符 {MEDIA_SLOT_TOKEN}。"
        "如不需要展示媒体，不要输出该占位符。"
    )
    system_prompt = f"{base_prompt}\n\n{role_hint}\n{tone_hint}\n{emotion_hint}\n{citation_hint}{media_slot_hint}"

    if risk_level == "medium" and knowledge_context:
        system_prompt += (
            f"\n\n{medium_knowledge_instructions}"
            f"\n\n{knowledge_context}"
        )

    # Build message history (last 10 messages from conversation)
    messages = [{"role": "system", "content": system_prompt}]

    # Add recent conversation history
    for msg in (conversation.messages or [])[-10:]:
        if not msg.is_deleted:
            messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": user_message})

    # Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=user_message,
        risk_level=risk_level,
        sensitive_words=filter_result.matched_words if filter_result.matched_words else None,
        sensitive_level=sensitive_level,
    )
    db.add(user_msg)

    # Step 7: LLM streaming call
    full_response = []
    model_version_used = "system"
    try:
        stream = await llm_router.chat(messages, stream=True)
        model_version_used = getattr(llm_router, "last_model_name", None) or "unknown"
        async for token in stream:
            if cancel_event and cancel_event.is_set():
                # Close the LLM stream
                if hasattr(stream, 'aclose'):
                    await stream.aclose()
                break
            full_response.append(token)
            yield {"type": "token", "content": token}
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        error_msg = "抱歉，系统暂时无法回答您的问题，请稍后重试。"
        full_response = [error_msg]
        yield {"type": "token", "content": error_msg}

    response_text = "".join(full_response)

    response_text, media_items = await _resolve_media_slots(response_text, user_message, db)

    # Step 8: Dual-model review (async — simplified inline for now)
    review_passed = True
    # In production, this would be dispatched as a Celery task

    # Step 9: Persist assistant message
    sources_payload = None
    if sources_citation and media_items:
        sources_payload = {
            "citations": sources_citation,
            "media_items": media_items,
        }
    elif media_items:
        sources_payload = {
            "media_items": media_items,
        }
    elif sources_citation:
        sources_payload = sources_citation

    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=response_text if response_text else "（已停止生成）",
        model_version=model_version_used,
        risk_level=risk_level,
        review_passed=review_passed,
        sources=sources_payload,
    )
    db.add(assistant_msg)
    await db.commit()

    yield {
        "type": "done",
        "content": response_text,
        "sources": sources_citation,
        "media_items": media_items,
        "risk_level": risk_level,
        "review_passed": review_passed,
    }
