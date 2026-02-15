"""SMS service with mock mode for development."""

import random
import string

from app.config import settings
from app.core.redis import redis_client

SMS_CODE_TTL = 300  # 5 minutes
SMS_RATE_LIMIT_TTL = 3600  # 1 hour
SMS_RATE_LIMIT_MAX = 5
SMS_COOLDOWN = 60  # seconds between sends

MOCK_CODE = "123456"


async def send_sms_code(phone: str) -> dict:
    """Send SMS verification code. In mock mode, code is always 123456."""
    # Check cooldown
    cooldown_key = f"sms_cooldown:{phone}"
    if await redis_client.exists(cooldown_key):
        return {"success": False, "message": "发送过于频繁，请60秒后重试"}

    # Check rate limit
    rate_key = f"sms_limit:{phone}"
    count = await redis_client.get(rate_key)
    if count and int(count) >= SMS_RATE_LIMIT_MAX:
        return {"success": False, "message": "短信发送次数超限，请1小时后重试"}

    # Generate code
    if settings.SMS_MOCK:
        code = MOCK_CODE
    else:
        code = "".join(random.choices(string.digits, k=6))
        # TODO: Call real SMS provider (Aliyun/Tencent Cloud)

    # Store code in Redis
    await redis_client.set(f"sms:{phone}", code, ex=SMS_CODE_TTL)
    await redis_client.set(cooldown_key, "1", ex=SMS_COOLDOWN)

    # Increment rate limit
    pipe = redis_client.pipeline()
    await pipe.incr(rate_key)
    await pipe.expire(rate_key, SMS_RATE_LIMIT_TTL)
    await pipe.execute()

    return {"success": True, "message": "验证码已发送"}


async def verify_sms_code(phone: str, code: str) -> bool:
    """Verify SMS code against stored value."""
    stored_code = await redis_client.get(f"sms:{phone}")
    if not stored_code:
        return False
    if stored_code != code:
        return False
    # Delete code after successful verification
    await redis_client.delete(f"sms:{phone}")
    return True
