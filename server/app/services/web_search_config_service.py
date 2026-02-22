"""Web search (Tavily) configuration service.

Stores config in the ``system_configs`` table under the key
``web_search_tavily``.  Follows the same pattern as
``system_config_service.py``.
"""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.system_config import SystemConfig

WEB_SEARCH_CONFIG_KEY = "web_search_tavily"

VALID_SEARCH_DEPTHS = ("ultra-fast", "fast", "basic", "advanced")
VALID_TOPICS = ("general", "news", "finance")
VALID_TIME_RANGES = ("", "day", "week", "month", "year")
VALID_INCLUDE_ANSWER = (False, True, "basic", "advanced")
VALID_INCLUDE_RAW_CONTENT = (False, True, "markdown", "text")

# Tavily supported country names (lowercase)
VALID_COUNTRIES = {
    "", "afghanistan", "albania", "algeria", "andorra", "angola", "argentina",
    "armenia", "australia", "austria", "azerbaijan", "bahamas", "bahrain",
    "bangladesh", "barbados", "belarus", "belgium", "belize", "benin", "bhutan",
    "bolivia", "bosnia and herzegovina", "botswana", "brazil", "brunei",
    "bulgaria", "burkina faso", "burundi", "cambodia", "cameroon", "canada",
    "cape verde", "central african republic", "chad", "chile", "china",
    "colombia", "comoros", "congo", "costa rica", "croatia", "cuba", "cyprus",
    "czech republic", "denmark", "djibouti", "dominican republic", "ecuador",
    "egypt", "el salvador", "equatorial guinea", "eritrea", "estonia",
    "ethiopia", "fiji", "finland", "france", "gabon", "gambia", "georgia",
    "germany", "ghana", "greece", "guatemala", "guinea", "haiti", "honduras",
    "hungary", "iceland", "india", "indonesia", "iran", "iraq", "ireland",
    "israel", "italy", "jamaica", "japan", "jordan", "kazakhstan", "kenya",
    "kuwait", "kyrgyzstan", "latvia", "lebanon", "lesotho", "liberia", "libya",
    "liechtenstein", "lithuania", "luxembourg", "madagascar", "malawi",
    "malaysia", "maldives", "mali", "malta", "mauritania", "mauritius",
    "mexico", "moldova", "monaco", "mongolia", "montenegro", "morocco",
    "mozambique", "myanmar", "namibia", "nepal", "netherlands", "new zealand",
    "nicaragua", "niger", "nigeria", "north korea", "north macedonia", "norway",
    "oman", "pakistan", "panama", "papua new guinea", "paraguay", "peru",
    "philippines", "poland", "portugal", "qatar", "romania", "russia", "rwanda",
    "saudi arabia", "senegal", "serbia", "singapore", "slovakia", "slovenia",
    "somalia", "south africa", "south korea", "south sudan", "spain",
    "sri lanka", "sudan", "sweden", "switzerland", "syria", "taiwan",
    "tajikistan", "tanzania", "thailand", "togo", "trinidad and tobago",
    "tunisia", "turkey", "turkmenistan", "uganda", "ukraine",
    "united arab emirates", "united kingdom", "united states", "uruguay",
    "uzbekistan", "venezuela", "vietnam", "yemen", "zambia", "zimbabwe",
}

DEFAULT_CONFIG: dict = {
    "enabled": True,
    "api_key": "",
    "search_depth": "basic",
    "max_results": 10,
    "include_domains": [],
    "exclude_domains": [],
    "include_answer": False,
    "include_raw_content": False,
    "topic": "general",
    "country": "",
    "time_range": "",
    "chunks_per_source": 3,
    "include_images": False,
}

_cache: dict | None = None

# Pattern that matches a masked key produced by ``_mask_key``.
_MASKED_RE = re.compile(r"^.{0,8}\*{4}.{0,8}$")


def _normalize(config: dict | None, *, existing_key: str = "") -> dict:
    """Normalise and validate incoming config, returning a clean copy."""
    result = deepcopy(DEFAULT_CONFIG)
    if not isinstance(config, dict):
        result["api_key"] = existing_key or settings.TAVILY_API_KEY
        return result

    # enabled
    result["enabled"] = bool(config.get("enabled", DEFAULT_CONFIG["enabled"]))

    # api_key — preserve existing key when the incoming value is masked or empty
    raw_key = str(config.get("api_key", "")).strip()
    if not raw_key or _MASKED_RE.match(raw_key):
        result["api_key"] = existing_key or settings.TAVILY_API_KEY
    else:
        result["api_key"] = raw_key

    sd = str(config.get("search_depth", "basic")).strip().lower()
    result["search_depth"] = sd if sd in VALID_SEARCH_DEPTHS else "basic"

    mr = config.get("max_results", 10)
    result["max_results"] = max(1, min(20, int(mr))) if isinstance(mr, (int, float)) else 10

    for key in ("include_domains", "exclude_domains"):
        val = config.get(key, [])
        if isinstance(val, list):
            result[key] = [str(d).strip().lower() for d in val if str(d).strip()]
        else:
            result[key] = []

    # include_answer: bool or "basic"/"advanced"
    ia = config.get("include_answer", DEFAULT_CONFIG["include_answer"])
    if ia in VALID_INCLUDE_ANSWER:
        result["include_answer"] = ia
    elif isinstance(ia, str) and ia.lower() in ("basic", "advanced"):
        result["include_answer"] = ia.lower()
    else:
        result["include_answer"] = bool(ia)

    # include_raw_content: bool or "markdown"/"text"
    irc = config.get("include_raw_content", DEFAULT_CONFIG["include_raw_content"])
    if irc in VALID_INCLUDE_RAW_CONTENT:
        result["include_raw_content"] = irc
    elif isinstance(irc, str) and irc.lower() in ("markdown", "text"):
        result["include_raw_content"] = irc.lower()
    else:
        result["include_raw_content"] = bool(irc)

    topic = str(config.get("topic", "general")).strip().lower()
    result["topic"] = topic if topic in VALID_TOPICS else "general"

    # country — full lowercase name (e.g. "china", "united states")
    country = str(config.get("country", "")).strip().lower()
    result["country"] = country if country in VALID_COUNTRIES else ""

    # time_range
    tr = str(config.get("time_range", "")).strip().lower()
    result["time_range"] = tr if tr in VALID_TIME_RANGES else ""

    # chunks_per_source — 1-3, only effective with advanced depth
    cps = config.get("chunks_per_source", 3)
    result["chunks_per_source"] = max(1, min(3, int(cps))) if isinstance(cps, (int, float)) else 3

    # include_images
    result["include_images"] = bool(config.get("include_images", False))

    return result


def _mask_key(key: str) -> str:
    if not key or len(key) <= 8:
        return "****" if key else ""
    return f"{key[:4]}****{key[-4:]}"


# ── Cache helpers ────────────────────────────────────────────

def get_cached() -> dict:
    if _cache is None:
        return deepcopy(DEFAULT_CONFIG)
    return deepcopy(_cache)


def get_api_key() -> str:
    """Return the raw (unmasked) API key for making actual API calls."""
    cached = _cache or DEFAULT_CONFIG
    return cached.get("api_key", "") or settings.TAVILY_API_KEY


def is_enabled() -> bool:
    """Return whether web search is globally enabled."""
    cached = _cache or DEFAULT_CONFIG
    return bool(cached.get("enabled", True))


def _refresh(config: dict) -> None:
    global _cache
    _cache = deepcopy(config)


# ── DB operations ────────────────────────────────────────────

async def get_config(db: AsyncSession) -> dict:
    """Load config from DB (creating default row if missing), refresh cache."""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key == WEB_SEARCH_CONFIG_KEY)
    )
    item = result.scalar_one_or_none()

    if item is None:
        value = _normalize(None)
        item = SystemConfig(
            key=WEB_SEARCH_CONFIG_KEY,
            value=value,
            description="网页搜索(Tavily)配置",
        )
        db.add(item)
        await db.commit()
        _refresh(value)
        return get_cached()

    normalized = _normalize(item.value, existing_key=item.value.get("api_key", ""))
    if normalized != item.value:
        item.value = normalized
        item.updated_at = datetime.now(timezone.utc)
        await db.commit()
    _refresh(normalized)
    return get_cached()


async def update_config(config: dict, admin_id: str, db: AsyncSession) -> dict:
    """Update config in DB and refresh cache."""
    # Fetch existing key so masked values are preserved
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key == WEB_SEARCH_CONFIG_KEY)
    )
    item = result.scalar_one_or_none()
    existing_key = (item.value.get("api_key", "") if item and item.value else "") or settings.TAVILY_API_KEY

    normalized = _normalize(config, existing_key=existing_key)

    if item is None:
        item = SystemConfig(
            key=WEB_SEARCH_CONFIG_KEY,
            value=normalized,
            description="网页搜索(Tavily)配置",
            updated_by=admin_id,
        )
        db.add(item)
    else:
        item.value = normalized
        item.updated_by = admin_id
        item.updated_at = datetime.now(timezone.utc)

    await db.commit()
    _refresh(normalized)
    return get_cached()
