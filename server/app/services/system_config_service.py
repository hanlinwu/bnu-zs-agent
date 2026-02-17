"""System config service for chat guardrail and prompt settings."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_config import SystemConfig


CHAT_GUARDRAIL_CONFIG_KEY = "chat_guardrail"


DEFAULT_CHAT_GUARDRAIL_CONFIG = {
    "risk": {
        "high_keywords": [
            "保证录取", "一定能上", "包过", "内部名额", "走后门", "关系户",
            "最低分数线", "确切分数", "保底", "承诺", "100%",
            "退学费", "违约金", "法律", "投诉", "举报",
        ],
        "medium_keywords": [
            "分数线", "录取率", "学费", "奖学金金额", "就业率", "薪资",
            "排名", "招生人数", "报录比", "调剂", "复试线",
            "宿舍费", "住宿", "报名时间", "截止日期",
        ],
        "medium_topics": [
            "录取", "招生", "报名", "复试", "初试", "调剂", "推免", "保研",
            "学费", "奖学金", "住宿", "宿舍", "专业", "学制", "毕业", "就业",
            "申请", "材料", "条件", "要求", "名额", "计划", "政策", "时间",
        ],
        "medium_specific_hints": [
            "多少", "几号", "几月", "哪天", "什么时候", "截止", "最后", "具体", "准确",
            "最低", "最高", "分", "排名", "条件", "要求", "流程", "金额", "费用", "学制",
            "比例", "概率", "是否可以", "能不能", "需要什么", "要不要",
        ],
    },
    "prompts": {
        "medium_system_prompt": "你是北京师范大学招生智能助手\"京师小智\"。你的职责是基于北京师范大学官方资料，为考生和家长提供准确、友好的招生咨询服务。\n\n核心规则：\n1. 所有回答必须基于知识库中的官方资料，不得编造信息\n2. 涉及具体数字（分数线、学费、招生人数等）时必须引用来源\n3. 不确定的信息请建议用户联系招生办（电话：010-58807962）\n4. 保持北京师范大学\"学为人师，行为世范\"的校训精神\n5. 严禁做出任何录取承诺或保证",
        "low_system_prompt": "你是北京师范大学招生智能助手\"京师小智\"。请使用自然、友好、简洁的语气回答。\n\n规则：\n1. 不得做出录取承诺或保证\n2. 涉及你不确定的招生政策/数据时，明确说明并建议联系招生办（010-58807962）\n3. 回答优先清晰、实用，不要过度冗长",
        "medium_citation_hint": "重要：本次回答必须引用知识库来源，使用\"根据《xxx》…\"格式。",
        "medium_knowledge_instructions": "以下是相关知识库内容，请严格基于这些内容回答：\n1. 只使用来源中出现的信息，不得补充来源外事实\n2. 对关键结论使用“根据《文档名》...”表述\n3. 若来源信息不足，明确说明“知识库未提供该信息”并建议联系招生办",
        "high_risk_response": "这个问题涉及具体的招生政策和录取标准，为确保信息准确，建议您直接联系北京师范大学招生办：\n\n📞 电话：010-58807962\n🌐 官网：admission.bnu.edu.cn\n\n招生老师会为您提供最权威的解答。",
        "no_knowledge_response": "当前未检索到可验证的北京师范大学官方资料，暂时无法给出准确答复。\n\n建议您提供更具体的问题（如专业名称、招生类型、年份），或直接联系招生办：\n\n📞 电话：010-58807962\n🌐 官网：admission.bnu.edu.cn",
    },
}


_chat_guardrail_cache: dict = deepcopy(DEFAULT_CHAT_GUARDRAIL_CONFIG)


def _merge_dict(base: dict, override: dict | None) -> dict:
    result = deepcopy(base)
    if not isinstance(override, dict):
        return result
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def _normalize_chat_guardrail_config(config: dict | None) -> dict:
    merged = _merge_dict(DEFAULT_CHAT_GUARDRAIL_CONFIG, config)
    risk = merged.get("risk", {})
    prompts = merged.get("prompts", {})

    for key in ["high_keywords", "medium_keywords", "medium_topics", "medium_specific_hints"]:
        value = risk.get(key, [])
        if not isinstance(value, list):
            risk[key] = []
            continue
        risk[key] = [str(item).strip() for item in value if str(item).strip()]

    for key in [
        "medium_system_prompt",
        "low_system_prompt",
        "medium_citation_hint",
        "medium_knowledge_instructions",
        "high_risk_response",
        "no_knowledge_response",
    ]:
        prompts[key] = str(prompts.get(key, "")).strip() or DEFAULT_CHAT_GUARDRAIL_CONFIG["prompts"][key]

    merged["risk"] = risk
    merged["prompts"] = prompts
    return merged


def get_chat_guardrail_config_cached() -> dict:
    """Read in-memory chat guardrail config."""
    return deepcopy(_chat_guardrail_cache)


def _refresh_cache(config: dict) -> None:
    global _chat_guardrail_cache
    _chat_guardrail_cache = _normalize_chat_guardrail_config(config)


async def ensure_chat_guardrail_config(db: AsyncSession) -> dict:
    """Ensure chat guardrail config exists in DB, returning normalized value."""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == CHAT_GUARDRAIL_CONFIG_KEY))
    item = result.scalar_one_or_none()
    if item is None:
        value = deepcopy(DEFAULT_CHAT_GUARDRAIL_CONFIG)
        item = SystemConfig(
            key=CHAT_GUARDRAIL_CONFIG_KEY,
            value=value,
            description="聊天风险判定与分级提示词配置",
        )
        db.add(item)
        await db.commit()
        _refresh_cache(value)
        return get_chat_guardrail_config_cached()

    normalized = _normalize_chat_guardrail_config(item.value)
    if normalized != item.value:
        item.value = normalized
        item.updated_at = datetime.now(timezone.utc)
        await db.commit()
    _refresh_cache(normalized)
    return get_chat_guardrail_config_cached()


async def get_chat_guardrail_config(db: AsyncSession) -> dict:
    """Get chat guardrail config from DB and refresh cache."""
    return await ensure_chat_guardrail_config(db)


async def update_chat_guardrail_config(config: dict, admin_id: str, db: AsyncSession) -> dict:
    """Update chat guardrail config and refresh in-memory cache."""
    normalized = _normalize_chat_guardrail_config(config)
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == CHAT_GUARDRAIL_CONFIG_KEY))
    item = result.scalar_one_or_none()
    if item is None:
        item = SystemConfig(
            key=CHAT_GUARDRAIL_CONFIG_KEY,
            value=normalized,
            description="聊天风险判定与分级提示词配置",
            updated_by=admin_id,
        )
        db.add(item)
    else:
        item.value = normalized
        item.updated_by = admin_id
        item.updated_at = datetime.now(timezone.utc)

    await db.commit()
    _refresh_cache(normalized)
    return get_chat_guardrail_config_cached()
