"""SMS service with mock mode for development."""

import json
import random
import string
import asyncio

from alibabacloud_dypnsapi20170525.client import Client as DypnsapiClient
from alibabacloud_dypnsapi20170525 import models as dypns_models
from alibabacloud_tea_openapi import models as open_api_models


from app.config import settings
from app.core.redis import redis_client

SMS_CODE_TTL = 300  # 5 minutes
SMS_RATE_LIMIT_TTL = 3600  # 1 hour
SMS_RATE_LIMIT_MAX = 5
SMS_COOLDOWN = 60  # seconds between sends

MOCK_CODE = "123456"


def _must_get_aliyun_sms_config() -> dict:
    config = {
        "access_key_id": settings.SMS_ALIYUN_ACCESS_KEY_ID,
        "access_key_secret": settings.SMS_ALIYUN_ACCESS_KEY_SECRET,
        "sign_name": settings.SMS_ALIYUN_SIGN_NAME,
        "template_code": settings.SMS_ALIYUN_TEMPLATE_CODE,
        "template_min": settings.SMS_ALIYUN_TEMPLATE_MIN,
        "endpoint": settings.SMS_ALIYUN_ENDPOINT,
        "scheme_name": settings.SMS_ALIYUN_SCHEME_NAME,
    }
    required_keys = ["access_key_id", "access_key_secret", "sign_name", "template_code", "endpoint"]
    missing = [key for key in required_keys if not config.get(key)]
    if missing:
        raise ValueError(f"阿里云短信配置缺失: {', '.join(missing)}")
    return config


def _create_aliyun_client(config: dict) -> DypnsapiClient:
    client_config = open_api_models.Config(
        access_key_id=config["access_key_id"],
        access_key_secret=config["access_key_secret"],
    )
    client_config.endpoint = config["endpoint"]
    return DypnsapiClient(client_config)


def _send_sms_with_aliyun_sync(phone: str, code: str, config: dict) -> tuple[bool, str]:
    client = _create_aliyun_client(config)
    template_param = {
        "code": code,
        "min": str(config.get("template_min") or "5"),
    }
    request = dypns_models.SendSmsVerifyCodeRequest(
        phone_number=phone,
        sign_name=config["sign_name"],
        template_code=config["template_code"],
        template_param=json.dumps(template_param, ensure_ascii=False, separators=(",", ":")),
    )
    if config.get("scheme_name"):
        request.scheme_name = config["scheme_name"]

    response = client.send_sms_verify_code(request)
    body = getattr(response, "body", None)
    if not body:
        return False, "短信发送失败: 阿里云返回为空"

    code_value = getattr(body, "code", None)
    message_value = getattr(body, "message", None)
    if code_value not in ("OK", "Success"):
        return False, f"短信发送失败: {code_value or 'Unknown'} - {message_value or 'Unknown'}"

    return True, "验证码已发送"


async def _send_sms_with_aliyun(phone: str, code: str) -> tuple[bool, str]:
    config = _must_get_aliyun_sms_config()
    try:
        return await asyncio.to_thread(_send_sms_with_aliyun_sync, phone, code, config)
    except Exception as error:
        return False, f"短信服务调用失败: {error}"


async def send_sms_code(phone: str, purpose: str = "default") -> dict:
    """Send SMS verification code. In mock mode, code is always 123456.

    Args:
        phone: Target phone number.
        purpose: Usage scene (e.g. "login", "password", "phone_change").
                 Different purposes have independent cooldowns and codes.
    """
    # Check cooldown (per purpose)
    cooldown_key = f"sms_cooldown:{purpose}:{phone}"
    if await redis_client.exists(cooldown_key):
        return {"success": False, "message": "发送过于频繁，请60秒后重试"}

    # Check rate limit (shared per phone across all purposes)
    rate_key = f"sms_limit:{phone}"
    count = await redis_client.get(rate_key)
    if count and int(count) >= SMS_RATE_LIMIT_MAX:
        return {"success": False, "message": "短信发送次数超限，请1小时后重试"}

    # Generate code
    if settings.SMS_MOCK:
        code = MOCK_CODE
        sent, send_message = True, "验证码已发送"
    else:
        code = "".join(random.choices(string.digits, k=6))
        try:
            sent, send_message = await _send_sms_with_aliyun(phone, code)
        except ValueError as error:
            return {"success": False, "message": str(error)}

    if not sent:
        return {"success": False, "message": send_message}

    # Store code in Redis (per purpose)
    await redis_client.set(f"sms:{purpose}:{phone}", code, ex=SMS_CODE_TTL)
    await redis_client.set(cooldown_key, "1", ex=SMS_COOLDOWN)

    # Increment rate limit
    pipe = redis_client.pipeline()
    await pipe.incr(rate_key)
    await pipe.expire(rate_key, SMS_RATE_LIMIT_TTL)
    await pipe.execute()

    return {"success": True, "message": send_message}


async def verify_sms_code(phone: str, code: str, purpose: str = "default") -> bool:
    """Verify SMS code against stored value.

    In mock mode, accept MOCK_CODE directly without requiring send first.

    Args:
        phone: Target phone number.
        code: The code to verify.
        purpose: Must match the purpose used when sending.
    """
    code_key = f"sms:{purpose}:{phone}"

    # Mock mode: accept fixed code without needing to send first
    if settings.SMS_MOCK and code == MOCK_CODE:
        # Clean up any stored code if exists
        await redis_client.delete(code_key)
        return True

    stored_code = await redis_client.get(code_key)
    if not stored_code:
        return False
    if stored_code != code:
        return False
    # Delete code after successful verification
    await redis_client.delete(code_key)
    return True
