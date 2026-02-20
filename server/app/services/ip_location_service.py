"""Resolve province from IP address."""

from __future__ import annotations

import ipaddress

import httpx

from app.config import settings

ENGLISH_PROVINCE_MAP: dict[str, str] = {
    "beijing": "北京市",
    "tianjin": "天津市",
    "shanghai": "上海市",
    "chongqing": "重庆市",
    "hebei": "河北省",
    "shanxi": "山西省",
    "liaoning": "辽宁省",
    "jilin": "吉林省",
    "heilongjiang": "黑龙江省",
    "jiangsu": "江苏省",
    "zhejiang": "浙江省",
    "anhui": "安徽省",
    "fujian": "福建省",
    "jiangxi": "江西省",
    "shandong": "山东省",
    "henan": "河南省",
    "hubei": "湖北省",
    "hunan": "湖南省",
    "guangdong": "广东省",
    "hainan": "海南省",
    "sichuan": "四川省",
    "guizhou": "贵州省",
    "yunnan": "云南省",
    "shaanxi": "陕西省",
    "gansu": "甘肃省",
    "qinghai": "青海省",
    "taiwan": "台湾省",
    "inner mongolia": "内蒙古自治区",
    "guangxi": "广西壮族自治区",
    "tibet": "西藏自治区",
    "ningxia": "宁夏回族自治区",
    "xinjiang": "新疆维吾尔自治区",
    "hong kong": "香港特别行政区",
    "macau": "澳门特别行政区",
}

CHINA_REGION_NORMALIZE: dict[str, str] = {
    "北京": "北京市",
    "北京市": "北京市",
    "天津": "天津市",
    "天津市": "天津市",
    "上海": "上海市",
    "上海市": "上海市",
    "重庆": "重庆市",
    "重庆市": "重庆市",
    "内蒙古": "内蒙古自治区",
    "广西": "广西壮族自治区",
    "西藏": "西藏自治区",
    "宁夏": "宁夏回族自治区",
    "新疆": "新疆维吾尔自治区",
    "香港": "香港特别行政区",
    "澳门": "澳门特别行政区",
}


def _is_public_ip(ip_text: str) -> bool:
    try:
        ip_obj = ipaddress.ip_address(ip_text)
    except ValueError:
        return False
    return not (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_link_local
    )


def _normalize_cn_province(raw: str | None) -> str | None:
    if not raw:
        return None
    value = raw.strip()
    if not value:
        return None

    lower = value.lower()
    if lower in ENGLISH_PROVINCE_MAP:
        return ENGLISH_PROVINCE_MAP[lower]

    if value in CHINA_REGION_NORMALIZE:
        return CHINA_REGION_NORMALIZE[value]

    if value.endswith(("省", "市", "自治区", "特别行政区")):
        return value[:20]

    if value in {"河北", "山西", "辽宁", "吉林", "黑龙江", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南", "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海", "台湾"}:
        return f"{value}省"

    return value[:20]


async def _lookup_primary(ip_text: str) -> str | None:
    url = settings.IP_GEO_LOOKUP_PRIMARY_URL.format(ip=ip_text)
    timeout = httpx.Timeout(settings.IP_GEO_LOOKUP_TIMEOUT_SEC)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url)
    if resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("status") != "success":
        return None
    country_code = str(data.get("countryCode") or "").upper()
    if country_code != "CN":
        return None
    return _normalize_cn_province(data.get("regionName"))


async def _lookup_secondary(ip_text: str) -> str | None:
    url = settings.IP_GEO_LOOKUP_SECONDARY_URL.format(ip=ip_text)
    timeout = httpx.Timeout(settings.IP_GEO_LOOKUP_TIMEOUT_SEC)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url)
    if resp.status_code != 200:
        return None
    data = resp.json()
    if not data.get("success", True):
        return None
    country_code = str(data.get("country_code") or "").upper()
    if country_code != "CN":
        return None
    return _normalize_cn_province(data.get("region"))


async def detect_province_by_ip(ip_text: str | None) -> str | None:
    """Detect Chinese province from client IP."""
    if not settings.IP_GEO_LOOKUP_ENABLED or not ip_text:
        return None
    if not _is_public_ip(ip_text):
        return None

    try:
        province = await _lookup_primary(ip_text)
        if province:
            return province
    except Exception:
        pass

    try:
        province = await _lookup_secondary(ip_text)
        if province:
            return province
    except Exception:
        pass

    return None

