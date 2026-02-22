"""Core chat orchestration service — the 9-step pipeline."""

import asyncio
import json
import logging
import math
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.sensitive_service import check_sensitive
from app.services.risk_service import classify_risk
from app.services.emotion_service import detect_emotion
from app.services.calendar_service import get_current_admission_context
from app.services.knowledge_service import search as knowledge_search, format_sources_for_prompt, format_sources_for_citation
from app.services.system_config_service import get_chat_guardrail_config_cached, get_system_basic_config_cached
from app.services.llm_service import llm_router
from app.services.media_match_service import match_media_for_question
from app.services import tavily_service, web_search_config_service

logger = logging.getLogger(__name__)
MEDIA_SLOT_TOKEN = "[[MEDIA_SLOT]]"
MEDIA_SLOT_REGEX = re.compile(r"\[\[\s*MEDIA_(?:SLOT|SOLT)\s*\]\]", re.IGNORECASE)
MEDIA_TAGGED_SLOT_REGEX = re.compile(r"\[\[\s*MEDIA_(?:SLOT|SOLT)\s*:\s*([^\]]+?)\s*\]\]", re.IGNORECASE)
MEDIA_INLINE_MARKER_REGEX = re.compile(r"\[\[\s*MEDIA_ITEM:([^\]]+)\s*\]\]")
JSON_OBJ_REGEX = re.compile(r"\{[\s\S]*\}")
ALLOWED_TOOLS = {"knowledge_search", "web_search", "media_search"}


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


def _extract_json_obj(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass
    matched = JSON_OBJ_REGEX.search(raw)
    if not matched:
        return None
    try:
        obj = json.loads(matched.group(0))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _truncate(text: str, limit: int) -> str:
    val = (text or "").strip()
    if len(val) <= limit:
        return val
    return val[:limit].rstrip() + "..."


def _normalize_tools(raw_tools: Any) -> list[str]:
    if isinstance(raw_tools, str):
        raw_tools = [raw_tools]
    if not isinstance(raw_tools, list):
        return []
    uniq: list[str] = []
    for item in raw_tools:
        tool = str(item or "").strip().lower()
        if tool in ALLOWED_TOOLS and tool not in uniq:
            uniq.append(tool)
    return uniq


def _build_decision_think_block(
    risk_level: str,
    tools: list[str],
    query: str,
    reason: str,
) -> str:
    del risk_level  # Hidden from user-facing think block.
    tools_text = "、".join(tools) if tools else "不调用外部检索工具"
    query_text = _truncate(query or "当前问题原文", 120)
    reason_text = _truncate(reason or "规则兜底", 160)
    # Never expose risk labels/details in user-facing think text.
    reason_text = re.sub(r"风险等级[:：]?\s*(low|medium|high|低|中|高)?", "", reason_text, flags=re.IGNORECASE)
    reason_text = re.sub(r"\b(low|medium|high)\b", "", reason_text, flags=re.IGNORECASE)
    reason_text = re.sub(r"\s{2,}", " ", reason_text).strip(" ，,;；。")
    if not reason_text:
        reason_text = "问题语义与检索需求判断"
    think_sentence = (
        f"我先根据问题意图选择了{tools_text}，并围绕“{query_text}”组织检索与回答，"
        f"主要依据是：{reason_text}。"
    )
    return (
        "<think>"
        f"{think_sentence}"
        "</think>\n\n"
    )


def _tokenize_for_bm25(text: str) -> list[str]:
    raw = (text or "").lower().strip()
    if not raw:
        return []
    chunks = re.findall(r"[\u4e00-\u9fff]+|[a-z0-9]+", raw)
    tokens: list[str] = []
    for chunk in chunks:
        # Chinese chunk: add unigram + bigram to improve short-query matching.
        if re.fullmatch(r"[\u4e00-\u9fff]+", chunk):
            chars = list(chunk)
            tokens.extend(chars)
            if len(chars) >= 2:
                tokens.extend([chars[i] + chars[i + 1] for i in range(len(chars) - 1)])
        else:
            tokens.append(chunk)
    return tokens


def _bm25_rerank_web_items(query: str, items: list[dict[str, Any]], top_k: int = 5) -> list[dict[str, Any]]:
    if not items:
        return []

    query_tokens = _tokenize_for_bm25(query)
    if not query_tokens:
        return items[:top_k]

    docs_tokens: list[list[str]] = []
    docs_tf: list[Counter[str]] = []
    for item in items:
        doc_text = f"{item.get('title', '')}\n{item.get('snippet', '')}"
        tokens = _tokenize_for_bm25(doc_text)
        docs_tokens.append(tokens)
        docs_tf.append(Counter(tokens))

    N = len(items)
    doc_lens = [len(tokens) for tokens in docs_tokens]
    avgdl = (sum(doc_lens) / N) if N else 1.0
    k1 = 1.5
    b = 0.75

    df: Counter[str] = Counter()
    for tokens in docs_tokens:
        for t in set(tokens):
            df[t] += 1

    query_tf = Counter(query_tokens)
    reranked: list[dict[str, Any]] = []
    for idx, item in enumerate(items):
        tf = docs_tf[idx]
        dl = max(1, doc_lens[idx])
        score = 0.0
        for term, qf in query_tf.items():
            term_tf = tf.get(term, 0)
            if term_tf <= 0:
                continue
            n_qi = df.get(term, 0)
            idf = math.log(1 + (N - n_qi + 0.5) / (n_qi + 0.5))
            numer = term_tf * (k1 + 1)
            denom = term_tf + k1 * (1 - b + b * dl / max(avgdl, 1e-6))
            score += idf * (numer / max(denom, 1e-9)) * qf

        # Keep provider score as tiny tie-breaker.
        provider_score = float(item.get("score") or 0.0)
        merged = dict(item)
        merged["bm25_score"] = round(score, 6)
        merged["score"] = round(score + 1e-3 * provider_score, 6)
        reranked.append(merged)

    reranked.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return reranked[:top_k]


async def _decide_risk_and_tools(user_message: str, guardrail_config: dict) -> dict[str, Any]:
    fallback_risk = classify_risk(user_message, config=guardrail_config)
    fallback_tools = ["knowledge_search"] if fallback_risk == "medium" else []
    decision = {
        "risk_level": fallback_risk,
        "tools": fallback_tools,
        "search_query": user_message,
        "reason": "fallback",
    }

    messages = [
        {
            "role": "system",
            "content": (
                "你是对话路由决策模型。根据用户问题，输出严格JSON，不要输出其他文本。\n"
                "字段要求：risk_level(low|medium|high), tools(string[]), search_query(string), reason(string)。\n"
                "tools 可选值：knowledge_search, web_search, media_search。\n"
                "决策规则：\n"
                "1) 高风险内容 risk_level=high，tools=[]。\n"
                "2) 涉及事实性问答可用 knowledge_search。\n"
                "3) 涉及时效信息、校外公开网页信息可加 web_search。\n"
                "4) 用户明确要图片/视频/校园环境展示可加 media_search。\n"
                "5) search_query 给出更适合检索的简短关键词。"
            ),
        },
        {"role": "user", "content": user_message},
    ]

    try:
        raw = await llm_router.decision_chat(messages)
        parsed = _extract_json_obj(raw)
        if not parsed:
            return decision
        risk_level = str(parsed.get("risk_level", "")).strip().lower()
        if risk_level not in ("low", "medium", "high"):
            risk_level = fallback_risk
        tools = _normalize_tools(parsed.get("tools"))
        query = str(parsed.get("search_query") or user_message).strip() or user_message
        reason = _truncate(str(parsed.get("reason") or ""), 160) or "decision_model"
        if risk_level == "high":
            tools = []
        return {
            "risk_level": risk_level,
            "tools": tools,
            "search_query": query,
            "reason": reason,
        }
    except Exception as e:
        logger.warning("Decision model failed, fallback to rules: %s", e)
        return decision


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

STAGE_LABELS = {
    "undergraduate": "本科",
    "master": "硕士研究生",
    "doctor": "博士研究生",
}
IDENTITY_LABELS = {
    "student": "学生本人",
    "parent": "家长",
}
SOURCE_GROUP_LABELS = {
    "mainland_general": "内地生",
    "hkmo_tw": "港澳台生",
    "international": "国际生",
}

async def process_message(
    user: User,
    conversation: Conversation,
    user_message: str,
    user_role: str | None,  # retained for API compatibility; no longer used for role routing.
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

    guardrail_config = get_chat_guardrail_config_cached()
    prompts_cfg = guardrail_config.get("prompts", {})
    high_risk_response = prompts_cfg.get("high_risk_response", "")

    # Step 1: Sensitive word pre-filter
    filter_result = await check_sensitive(user_message, db)
    sensitive_level = filter_result.highest_level if filter_result.matched_words else None

    # Hard short-circuit: once blocked by sensitive interception, do not call any model/tool.
    is_sensitive_block = (filter_result.action == "block") or (sensitive_level == "block")
    if is_sensitive_block:
        block_message = high_risk_response or "该问题属于高风险内容，建议咨询招生办获取权威答复。"
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
            content=block_message,
            model_version="system",
            risk_level="blocked",
        )
        db.add(assistant_msg)
        await db.commit()
        yield {"type": "sensitive_block", "content": block_message}
        return

    # Step 2: Decision model classification (risk + tool chain)
    no_knowledge_response = prompts_cfg.get("no_knowledge_response", "")
    medium_system_prompt = prompts_cfg.get("medium_system_prompt", "")
    low_system_prompt = prompts_cfg.get("low_system_prompt", "")
    medium_citation_hint_cfg = prompts_cfg.get("medium_citation_hint", "")
    medium_knowledge_instructions = prompts_cfg.get("medium_knowledge_instructions", "")

    decision = await _decide_risk_and_tools(user_message, guardrail_config)
    risk_level = decision["risk_level"]
    requested_tools: list[str] = decision["tools"]
    search_query: str = decision["search_query"]
    decision_reason: str = decision["reason"]
    think_block = _build_decision_think_block(
        risk_level=risk_level,
        tools=requested_tools,
        query=search_query,
        reason=decision_reason,
    )

    if risk_level == "high":
        msg = Message(conversation_id=conversation.id, role="user", content=user_message, risk_level="high")
        db.add(msg)
        high_risk_content = f"{think_block}{high_risk_response}"
        assistant_msg = Message(
            conversation_id=conversation.id, role="assistant",
            content=high_risk_content, model_version="system", risk_level="high",
        )
        db.add(assistant_msg)
        await db.commit()
        yield {"type": "high_risk", "content": high_risk_content}
        return

    # Step 3: Time/admission/system/user context injection
    admission_ctx = await get_current_admission_context(db)
    tone_config = admission_ctx.get("tone_config") or {}
    tone_hint = tone_config.get("system_hint", "")
    calendar_additional_prompt = str(admission_ctx.get("additional_prompt") or "").strip()
    stage_name = str(admission_ctx.get("stage_name") or "常态期")
    stage_year = int(admission_ctx.get("year") or datetime.now(timezone.utc).year)
    stage_start = str(admission_ctx.get("start_date") or "")
    stage_end = str(admission_ctx.get("end_date") or "")
    base_system_name = get_system_basic_config_cached().get("system_name") or "京师小智"
    cn_now = datetime.now(timezone(timedelta(hours=8)))
    now_text = cn_now.strftime("%Y-%m-%d %H:%M:%S")
    province = (getattr(user, "province", None) or "").strip()
    province_text = province if province else "未知"

    # Step 4: Emotion detection
    emotion = detect_emotion(user_message)
    emotion_hint = ""
    if emotion.comfort_prefix:
        emotion_hint = f"\n用户可能感到{emotion.emotion}，请在回答开头适当加入安慰和鼓励。"

    # Step 5: Decision-driven retrieval and context injection
    sources_citation: list[dict[str, Any]] = []
    retrieval_context_parts: list[str] = []
    tools_used: list[str] = []
    tool_traces: list[dict[str, Any]] = []
    media_search_items: list[dict[str, Any]] = []

    if "knowledge_search" in requested_tools and risk_level != "high":
        yield {"type": "tool_status", "tool": "knowledge_search", "status": "running", "query": search_query}
        search_results = await knowledge_search(
            search_query,
            db,
            top_k=5,
            recall_k=30,
            min_vector_score=0.18,
            min_hybrid_score=0.22,
        )
        if search_results:
            tools_used.append("knowledge_search")
            retrieval_context_parts.append(
                "【知识库检索】\n" + format_sources_for_prompt(search_results)
            )
            kb_citations = format_sources_for_citation(search_results)
            for item in kb_citations:
                sources_citation.append(
                    {
                        "source_type": "knowledge",
                        "doc_id": item.get("doc_id"),
                        "title": item.get("title"),
                        "snippet": item.get("chunk", ""),
                        "score": item.get("score"),
                    }
                )
            tool_traces.append(
                {
                    "tool": "knowledge_search",
                    "query": search_query,
                    "count": len(search_results),
                    "items": [
                        {
                            "title": r.document_title,
                            "snippet": _truncate(r.content, 240),
                            "score": round(r.score, 3),
                        }
                        for r in search_results
                    ],
                }
            )
        else:
            tool_traces.append(
                {"tool": "knowledge_search", "query": search_query, "count": 0, "items": []}
            )
        yield {"type": "tool_status", "tool": "knowledge_search", "status": "done", "query": search_query}

    if "web_search" in requested_tools and risk_level != "high":
        web_config = await web_search_config_service.get_config(db)
        if web_config.get("enabled", True) and web_search_config_service.get_api_key():
            yield {
                "type": "tool_status",
                "tool": "web_search",
                "status": "running",
                "query": search_query,
                "content": f"正在检索关键词「{search_query}」...",
            }
            web_items: list[dict[str, Any]] = []
            try:
                web_res = await tavily_service.search(
                    api_key=web_search_config_service.get_api_key(),
                    query=search_query,
                    search_depth=web_config.get("search_depth", "basic"),
                    max_results=web_config.get("max_results", 8),
                    include_domains=web_config.get("include_domains"),
                    exclude_domains=web_config.get("exclude_domains"),
                    include_answer=False,
                    include_raw_content=False,
                    topic=web_config.get("topic", "general"),
                    country=web_config.get("country", ""),
                    time_range=web_config.get("time_range", ""),
                    chunks_per_source=web_config.get("chunks_per_source", 3),
                    include_images=False,
                )
                raw_results = web_res.get("results") or []
                web_candidates = [
                    {
                        "title": str(r.get("title") or ""),
                        "url": str(r.get("url") or ""),
                        "snippet": _truncate(str(r.get("content") or ""), 260),
                        "score": float(r.get("score") or 0.0),
                    }
                    for r in raw_results
                ]
                web_items = _bm25_rerank_web_items(search_query, web_candidates, top_k=5)
            except Exception as e:
                logger.warning("Web search failed in chat pipeline: %s", e)

            if web_items:
                tools_used.append("web_search")
                retrieval_context_parts.append(
                    "【网页检索】\n"
                    + "\n\n".join(
                        [
                            f"[网页来源{i}] 标题：{item['title']}\nURL：{item['url']}\n内容：{item['snippet']}"
                            for i, item in enumerate(web_items, 1)
                        ]
                    )
                )
                for item in web_items:
                    sources_citation.append(
                        {
                            "source_type": "web",
                            "title": item["title"],
                            "snippet": item["snippet"],
                            "url": item["url"],
                            "score": round(item["score"], 3),
                        }
                    )
            tool_traces.append(
                {
                    "tool": "web_search",
                    "query": search_query,
                    "count": len(web_items),
                    "items": web_items,
                }
            )
            yield {"type": "tool_status", "tool": "web_search", "status": "done", "query": search_query}
        else:
            tool_traces.append(
                {
                    "tool": "web_search",
                    "query": search_query,
                    "count": 0,
                    "items": [],
                    "note": "web_search_disabled_or_no_key",
                }
            )

    if "media_search" in requested_tools and risk_level != "high":
        yield {"type": "tool_status", "tool": "media_search", "status": "running", "query": search_query}
        media_search_items = await match_media_for_question(search_query, db, limit=4)
        if media_search_items:
            tools_used.append("media_search")
            retrieval_context_parts.append(
                "【媒体检索】\n"
                + "\n".join(
                    [
                        f"- {item.get('title') or ''}（{item.get('media_type')}）"
                        f" 描述：{_truncate(item.get('description') or '', 120)}"
                        for item in media_search_items
                    ]
                )
            )
        tool_traces.append(
            {
                "tool": "media_search",
                "query": search_query,
                "count": len(media_search_items),
                "items": media_search_items,
            }
        )
        yield {"type": "tool_status", "tool": "media_search", "status": "done", "query": search_query}

    # 中风险且无任何检索结果：不进入自由生成
    if risk_level == "medium" and not sources_citation:
        user_msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=user_message,
            risk_level=risk_level,
            sensitive_words=filter_result.matched_words if filter_result.matched_words else None,
            sensitive_level=sensitive_level,
        )
        db.add(user_msg)

        sources_payload = {
            "citations": [],
            "tools_used": tools_used,
            "tool_traces": tool_traces,
            "decision": {
                "risk_level": risk_level,
                "tools": requested_tools,
                "query": search_query,
                "reason": decision_reason,
            },
        }
        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=f"{think_block}{no_knowledge_response}",
            model_version="system",
            risk_level=risk_level,
            review_passed=True,
            sources=sources_payload,
        )
        db.add(assistant_msg)
        await db.commit()

        yield {"type": "token", "content": f"{think_block}{no_knowledge_response}"}
        yield {
            "type": "done",
            "content": f"{think_block}{no_knowledge_response}",
            "sources": [],
            "tools_used": tools_used,
            "tool_traces": tool_traces,
            "risk_level": risk_level,
            "review_passed": True,
        }
        return

    # Step 6: Prompt assembly
    identity_type = (getattr(user, "identity_type", None) or "").strip().lower()
    identity_label = IDENTITY_LABELS.get(identity_type, "未设置")
    identity_hint = ""
    if identity_type == "parent":
        identity_hint = "用户身份为家长，请适当补充家长关心的培养质量、就业发展与校园保障信息。"
    elif identity_type == "student":
        identity_hint = "用户身份为学生本人，请优先提供报考、学习与发展路径的直接建议。"

    source_group = (getattr(user, "source_group", None) or "").strip().lower()
    source_group_label = SOURCE_GROUP_LABELS.get(source_group, "未设置")
    source_group_hint = ""
    if source_group == "hkmo_tw":
        source_group_hint = "用户生源类型为港澳台生，请优先说明港澳台相关招生政策、报名方式和材料要求。"
    elif source_group == "international":
        source_group_hint = "用户生源类型为国际生，请优先说明国际学生申请路径、语言与材料要求。"
    elif source_group == "mainland_general":
        source_group_hint = "用户生源类型为内地生，请优先采用内地普通招生语境组织回答。"

    stages_raw = (getattr(user, "admission_stages", None) or "").strip()
    stage_codes = [s.strip() for s in stages_raw.split(",") if s.strip()]
    stage_labels = [STAGE_LABELS[s] for s in stage_codes if s in STAGE_LABELS]
    stage_text = "、".join(stage_labels) if stage_labels else "未设置"
    stage_hint = ""
    if stage_labels:
        stage_hint = f"用户当前重点关注招生阶段：{stage_text}。回答时请优先覆盖这些阶段的信息。"
    citation_hint = ""
    if risk_level == "medium":
        citation_hint = f"\n{medium_citation_hint_cfg}" if medium_citation_hint_cfg else ""

    base_prompt = medium_system_prompt if risk_level == "medium" else low_system_prompt
    media_slot_hint = (
        f"\n\n如果用户问题涉及校园环境、校园生活、宿舍、食堂、图书馆、教学设施，"
        f"或用户明确希望查看图片/视频，请在回答中单独输出占位符 {MEDIA_SLOT_TOKEN}。"
        "如不需要展示媒体，不要输出该占位符。"
    )
    prompt_context_parts = [
        f"系统名称：{base_system_name}",
        f"当前时间：{now_text}（UTC+8）",
        f"当前招生阶段：{stage_year}年 {stage_name}",
        f"用户省份：{province_text}",
        f"用户身份：{identity_label}",
        f"用户生源类型：{source_group_label}",
        f"用户关注阶段：{stage_text}",
    ]
    if stage_start and stage_end:
        prompt_context_parts.append(f"阶段日期：{stage_start} ~ {stage_end}")
    prompt_context = "\n".join(prompt_context_parts)

    system_prompt = (
        f"{base_prompt}\n\n"
        f"{prompt_context}\n"
        f"{identity_hint}\n"
        f"{source_group_hint}\n"
        f"{stage_hint}\n"
        f"{tone_hint}\n"
        f"{emotion_hint}\n"
        f"{citation_hint}{media_slot_hint}"
    )
    if calendar_additional_prompt:
        system_prompt += f"\n\n招生日历附加要求：{calendar_additional_prompt}"

    if retrieval_context_parts:
        system_prompt += (
            f"\n\n{medium_knowledge_instructions}"
            "\n\n以下是可用检索证据，请优先基于证据回答，不能编造来源：\n"
            + "\n\n".join(retrieval_context_parts)
        )

    # Build message history (last 10 messages from conversation)
    messages = [{"role": "system", "content": system_prompt}]

    # Query only recent messages to avoid loading full conversation history
    history_stmt = (
        select(Message)
        .where(
            and_(
                Message.conversation_id == conversation.id,
                Message.is_deleted == False,
            )
        )
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(10)
    )
    history_result = await db.execute(history_stmt)
    recent_messages = list(reversed(history_result.scalars().all()))

    for msg in recent_messages:
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
    if think_block:
        response_text = f"{think_block}{response_text}" if response_text else think_block

    response_text, media_items = await _resolve_media_slots(response_text, user_message, db)

    # Step 8: Dual-model review (async — simplified inline for now)
    review_passed = True
    # In production, this would be dispatched as a Celery task

    # Step 9: Persist assistant message
    sources_payload = None
    if sources_citation or media_items or tools_used or tool_traces:
        sources_payload = {
            "citations": sources_citation,
            "tools_used": tools_used,
            "tool_traces": tool_traces,
            "decision": {
                "risk_level": risk_level,
                "tools": requested_tools,
                "query": search_query,
                "reason": decision_reason,
            },
        }
    if media_items:
        if sources_payload is None:
            sources_payload = {}
        sources_payload["media_items"] = media_items
    elif media_search_items:
        # Keep media search results in trace; inline slots are optional.
        pass

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
        "tools_used": tools_used,
        "tool_traces": tool_traces,
        "risk_level": risk_level,
        "review_passed": review_passed,
    }
