"""Time-aware calendar service for admission-phase tone injection."""

import logging
from datetime import date, datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_client
from app.models.calendar import AdmissionCalendar

logger = logging.getLogger(__name__)

CACHE_KEY = "calendar:current"
CACHE_TTL = 86400  # 1 day

# Default tone configs when no calendar entry exists
DEFAULT_TONES = {
    "preparation": {
        "style": "encouraging",
        "keywords": ["备考", "加油", "规划"],
        "focus_topics": ["专业前景", "备考建议", "校园文化"],
        "system_hint": "当前为备考期（1-5月），请以激励、积极的口吻回答，侧重备考建议和专业前景介绍。",
    },
    "application": {
        "style": "practical",
        "keywords": ["志愿", "填报", "分数线"],
        "focus_topics": ["志愿填报", "分数线", "报名指南", "专业选择"],
        "system_hint": "当前为高考后报名期（6-7月），请以务实、详细的口吻回答，侧重志愿填报、分数线和报名流程。",
    },
    "admission": {
        "style": "warm",
        "keywords": ["录取", "通知书", "入学"],
        "focus_topics": ["录取查询", "入学准备", "新生指南"],
        "system_hint": "当前为录取查询期（8-9月），请以温暖、欢迎的口吻回答，侧重录取结果查询和入学准备。",
    },
    "normal": {
        "style": "friendly",
        "keywords": ["校园", "师资", "交流"],
        "focus_topics": ["校园文化", "师资力量", "国际交流", "校园生活"],
        "system_hint": "当前为常态期，请以友好、全面的口吻回答，介绍校园文化、师资和校园生活。",
    },
}


def _get_default_period(month: int) -> str:
    if 1 <= month <= 5:
        return "preparation"
    elif 6 <= month <= 7:
        return "application"
    elif 8 <= month <= 9:
        return "admission"
    else:
        return "normal"


async def get_current_tone(db: AsyncSession | None = None) -> dict:
    """Get current admission phase tone config.

    Returns tone_config dict with style, keywords, focus_topics, system_hint.
    """
    # Try cache
    try:
        cached = await redis_client.hgetall(CACHE_KEY)
        if cached:
            import json
            return json.loads(cached.get("tone_config", "{}"))
    except Exception:
        pass

    now = datetime.now(timezone.utc)
    today = now.date()
    month = now.month

    tone_config = None

    # Try DB
    if db:
        try:
            stmt = select(AdmissionCalendar).where(
                and_(
                    AdmissionCalendar.start_date <= today,
                    AdmissionCalendar.end_date >= today,
                    AdmissionCalendar.is_active == True,
                )
            )
            result = await db.execute(stmt)
            calendar = result.scalar_one_or_none()
            if calendar:
                tone_config = calendar.tone_config
        except Exception as e:
            logger.warning("Failed to load calendar from DB: %s", e)

    # Fallback to defaults
    if not tone_config:
        period = _get_default_period(month)
        tone_config = DEFAULT_TONES[period]

    # Cache
    try:
        import json
        await redis_client.hset(CACHE_KEY, mapping={"tone_config": json.dumps(tone_config, ensure_ascii=False)})
        await redis_client.expire(CACHE_KEY, CACHE_TTL)
    except Exception:
        pass

    return tone_config
