"""Core chat orchestration service — the 9-step pipeline."""

import logging
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
from app.services.llm_service import llm_router

logger = logging.getLogger(__name__)

# Role-specific system prompt fragments
ROLE_PROMPTS = {
    "gaokao": "用户是一名高考考生。请用鼓励、平易近人的口吻回答，侧重本科招生信息。",
    "kaoyan": "用户是一名考研学生。请用专业、详细的口吻回答，侧重研究生招生和学术方向。",
    "international": "用户是一名国际学生。请用清晰、友好的口吻回答，如有需要可用中英双语，侧重国际招生政策和留学生支持。",
    "parent": "用户是一名考生家长。请用耐心、温和、详细的口吻回答，侧重家长关心的就业前景、校园安全和学费。",
}

BASE_SYSTEM_PROMPT = """你是北京师范大学招生智能助手"京师小智"。你的职责是基于北京师范大学官方资料，为考生和家长提供准确、友好的招生咨询服务。

核心规则：
1. 所有回答必须基于知识库中的官方资料，不得编造信息
2. 涉及具体数字（分数线、学费、招生人数等）时必须引用来源
3. 不确定的信息请建议用户联系招生办（电话：010-58807962）
4. 保持北京师范大学"学为人师，行为世范"的校训精神
5. 严禁做出任何录取承诺或保证"""

HIGH_RISK_RESPONSE = "这个问题涉及具体的招生政策和录取标准，为确保信息准确，建议您直接联系北京师范大学招生办：\n\n📞 电话：010-58807962\n🌐 官网：admission.bnu.edu.cn\n\n招生老师会为您提供最权威的解答。"


async def process_message(
    user: User,
    conversation: Conversation,
    user_message: str,
    user_role: str | None,
    db: AsyncSession,
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
    if filter_result.action == "block":
        # Save blocked message
        msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=user_message,
            risk_level="blocked",
        )
        db.add(msg)
        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=filter_result.message,
            risk_level="blocked",
        )
        db.add(assistant_msg)
        await db.commit()
        yield {"type": "sensitive_block", "content": filter_result.message}
        return

    # Step 2: Risk classification
    risk_level = classify_risk(user_message)

    if risk_level == "high":
        msg = Message(conversation_id=conversation.id, role="user", content=user_message, risk_level="high")
        db.add(msg)
        assistant_msg = Message(
            conversation_id=conversation.id, role="assistant",
            content=HIGH_RISK_RESPONSE, risk_level="high",
        )
        db.add(assistant_msg)
        await db.commit()
        yield {"type": "high_risk", "content": HIGH_RISK_RESPONSE}
        return

    # Step 3: Time-aware tone injection
    tone_config = await get_current_tone(db)
    tone_hint = tone_config.get("system_hint", "")

    # Step 4: Emotion detection
    emotion = detect_emotion(user_message)
    emotion_hint = ""
    if emotion.comfort_prefix:
        emotion_hint = f"\n用户可能感到{emotion.emotion}，请在回答开头适当加入安慰和鼓励。"

    # Step 5: Knowledge base search
    search_results = await knowledge_search(user_message, db, top_k=5)
    knowledge_context = format_sources_for_prompt(search_results)
    sources_citation = format_sources_for_citation(search_results)

    # Step 6: Prompt assembly
    role_hint = ROLE_PROMPTS.get(user_role or "", "")
    citation_hint = ""
    if risk_level == "medium":
        citation_hint = '\n重要：本次回答必须引用知识库来源，使用"根据《xxx》…"格式。'

    system_prompt = f"{BASE_SYSTEM_PROMPT}\n\n{role_hint}\n{tone_hint}\n{emotion_hint}\n{citation_hint}"

    if knowledge_context:
        system_prompt += f"\n\n以下是相关知识库内容，请基于这些内容回答：\n\n{knowledge_context}"

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
    )
    db.add(user_msg)

    # Step 7: LLM streaming call
    full_response = []
    try:
        stream = await llm_router.chat(messages, stream=True)
        async for token in stream:
            full_response.append(token)
            yield {"type": "token", "content": token}
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        error_msg = "抱歉，系统暂时无法回答您的问题，请稍后重试。"
        full_response = [error_msg]
        yield {"type": "token", "content": error_msg}

    response_text = "".join(full_response)

    # Step 8: Dual-model review (async — simplified inline for now)
    review_passed = True
    # In production, this would be dispatched as a Celery task

    # Step 9: Persist assistant message
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=response_text,
        risk_level=risk_level,
        review_passed=review_passed,
        sources=sources_citation if sources_citation else None,
    )
    db.add(assistant_msg)
    await db.commit()

    yield {
        "type": "done",
        "sources": sources_citation,
        "risk_level": risk_level,
        "review_passed": review_passed,
    }
