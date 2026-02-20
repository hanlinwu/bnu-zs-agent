"""Application middleware: audit logging, rate limiting."""

import asyncio
import re
import time
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.config import settings
from app.core.security import verify_token
from app.services.audit_sqlite_service import append_audit_log
from app.services.request_ip_service import get_client_ip


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
                "ip_address": get_client_ip(request),
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
            client_ip = get_client_ip(request) or "unknown"
            logger.info(
                "request_id=%s method=%s path=%s status=%s duration_ms=%s ip=%s",
                request.state.request_id,
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                client_ip,
            )

        try:
            asyncio.create_task(self._write_audit_log(request, response, duration_ms))
        except Exception:
            # Audit logging failures must not break normal requests
            pass

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-based layered rate limiting.

    Priority:
    - Authenticated requests: limit by actor id (user/admin), reduce NAT collateral.
    - Anonymous requests: limit by ip + path.
    - Global IP guard: a wider cap to protect from floods.
    """

    ACTOR_RATE_LIMIT = 180
    ANON_RATE_LIMIT = 90
    IP_BURST_LIMIT = 600
    WINDOW_SECONDS = 60
    _UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)

    @classmethod
    def _normalize_route_key(cls, path: str) -> str:
        parts: list[str] = []
        for seg in path.split("/"):
            if not seg:
                continue
            low = seg.lower()
            if low.isdigit() or cls._UUID_RE.match(low):
                parts.append(":id")
            else:
                parts.append(low)
        if not parts:
            return "/"
        # Keep bounded cardinality.
        return "/" + "/".join(parts[:6])

    @staticmethod
    def _extract_actor_key(request: Request) -> str | None:
        auth = request.headers.get("authorization") or ""
        if not auth.startswith("Bearer "):
            return None

        token = auth[7:]
        try:
            payload = verify_token(token)
        except Exception:
            return None

        subject = payload.get("sub")
        actor_type = payload.get("type")
        if not subject or actor_type not in {"user", "admin"}:
            return None
        return f"{actor_type}:{subject}"

    async def _hit_limit(self, key: str, limit: int) -> bool:
        from app.core.redis import redis_client

        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, self.WINDOW_SECONDS)
        return current > limit

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ("/health",):
            return await call_next(request)

        client_ip = get_client_ip(request) or "unknown"
        actor_key = self._extract_actor_key(request)
        route_key = self._normalize_route_key(request.url.path)

        try:
            if await self._hit_limit(f"rate:ipburst:{client_ip}", self.IP_BURST_LIMIT):
                return JSONResponse(
                    status_code=429,
                    content={"detail": {"code": 429, "message": "请求过于频繁，请稍后再试"}},
                )

            if actor_key:
                if await self._hit_limit(f"rate:actor:{actor_key}", self.ACTOR_RATE_LIMIT):
                    return JSONResponse(
                        status_code=429,
                        content={"detail": {"code": 429, "message": "请求过于频繁，请稍后再试"}},
                    )
            else:
                if await self._hit_limit(f"rate:anon:{client_ip}:{route_key}", self.ANON_RATE_LIMIT):
                    return JSONResponse(
                        status_code=429,
                        content={"detail": {"code": 429, "message": "请求过于频繁，请稍后再试"}},
                    )
        except Exception:
            # If Redis is unavailable, allow the request through
            pass

        return await call_next(request)
