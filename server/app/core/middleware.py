"""Application middleware: audit logging, rate limiting."""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.config import settings


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Automatically log each request for audit trail."""

    async def dispatch(self, request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        start_time = time.time()

        response = await call_next(request)

        # Log async to avoid blocking — in production this would write to DB
        duration_ms = round((time.time() - start_time) * 1000, 2)
        # Structured log entry (written to stdout, collected by Docker logs)
        if request.url.path.startswith("/api/"):
            import logging
            logger = logging.getLogger("audit")
            logger.info(
                "request_id=%s method=%s path=%s status=%s duration_ms=%s ip=%s",
                request.state.request_id,
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                request.client.host if request.client else "unknown",
            )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-based IP rate limiting (120 requests/minute)."""

    RATE_LIMIT = 120
    WINDOW_SECONDS = 60

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ("/health",):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"

        try:
            from app.core.redis import redis_client
            key = f"rate:{client_ip}"
            current = await redis_client.incr(key)
            if current == 1:
                await redis_client.expire(key, self.WINDOW_SECONDS)
            if current > self.RATE_LIMIT:
                return JSONResponse(
                    status_code=429,
                    content={"detail": {"code": 429, "message": "请求过于频繁，请稍后再试"}},
                )
        except Exception:
            # If Redis is unavailable, allow the request through
            pass

        return await call_next(request)
