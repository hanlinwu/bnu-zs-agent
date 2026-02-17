"""Application middleware: audit logging, rate limiting."""

import asyncio
import time
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.config import settings
from app.core.security import verify_token
from app.services.audit_sqlite_service import append_audit_log


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Automatically log each request for audit trail."""

    @staticmethod
    def _action_from_method(method: str) -> str:
        mapping = {
            "GET": "query",
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete",
        }
        return mapping.get(method.upper(), "query")

    @staticmethod
    def _resource_from_path(path: str) -> str | None:
        """Extract resource name from /api/v1/{resource} or /api/v1/admin/{resource} path."""
        if not path.startswith("/api/v1/"):
            return None

        segments = [seg for seg in path.split("/") if seg]
        # ['api', 'v1', ...]
        if len(segments) < 3:
            return None

        if segments[2] == "admin":
            if len(segments) >= 4:
                return segments[3]
            return "admin"
        return segments[2]

    @staticmethod
    def _extract_token_payload(request: Request) -> dict | None:
        """Decode bearer token payload if present."""
        auth = request.headers.get("authorization") or ""
        if not auth.startswith("Bearer "):
            return None

        token = auth[7:]
        try:
            return verify_token(token)
        except Exception:
            return None

    @staticmethod
    def _extract_actor_ids(payload: dict | None) -> tuple[str | None, str | None]:
        """Return (user_id, admin_id) from decoded token payload if available."""
        if not payload:
            return None, None

        actor_type = payload.get("type")
        subject = payload.get("sub")
        if not subject:
            return None, None

        if actor_type == "admin":
            return None, str(subject)
        if actor_type == "user":
            return str(subject), None
        return None, None

    async def _write_audit_log(self, request: Request, response: Response, duration_ms: float) -> None:
        path = request.url.path
        if not path.startswith("/api/"):
            return

        # Skip frequently-hit and self-observing endpoints
        if path in ("/health",) or path.startswith("/api/v1/admin/logs"):
            return

        action = self._action_from_method(request.method)
        resource = self._resource_from_path(path)
        payload = getattr(request.state, "token_payload", None)
        user_id, admin_id = self._extract_actor_ids(payload)

        query_params: dict[str, Any] = dict(request.query_params)
        detail = {
            "path": path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "query": query_params,
        }

        await append_audit_log(
            {
                "user_id": user_id,
                "admin_id": admin_id,
                "action": action,
                "resource": resource,
                "resource_id": None,
                "ip_address": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "detail": detail,
            }
        )

    async def dispatch(self, request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        request.state.token_payload = self._extract_token_payload(request)
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

        try:
            asyncio.create_task(self._write_audit_log(request, response, duration_ms))
        except Exception:
            # Audit logging failures must not break normal requests
            pass

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
