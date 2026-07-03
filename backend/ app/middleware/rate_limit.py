# app/middleware/rate_limit.py
#
# ⚠️ main.py imports `RateLimitMiddleware` from this module but never
# calls `app.add_middleware(RateLimitMiddleware)` anywhere — it only
# adds `SlowAPIMiddleware` (from the `slowapi` package), which already
# handles rate limiting via the `limiter` configured in main.py.
#
# This means one of two things is true:
#   1. This class is dead code left over from an earlier approach,
#      and the import line in main.py can just be deleted, OR
#   2. You intended to layer a second, custom rate limiter on top of
#      slowapi for some reason (e.g. a different limiting strategy
#      per-route) and forgot to wire it in.
#
# Providing a minimal, working implementation below so the import
# doesn't crash the app — but recommend removing this file and the
# import in main.py unless you specifically need behavior slowapi
# doesn't already give you.

import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding-window rate limiter.

    NOTE: in-memory means limits reset on every worker restart and
    are tracked separately per gunicorn worker process (you're running
    4 workers per the log output), so the effective limit is actually
    `max_requests * worker_count`. For real multi-worker rate limiting
    you'd want a shared backend (Redis) — which is exactly what
    slowapi + a Redis storage backend already gives you for free, if
    you go that route instead of this file.
    """

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        window_start = now - self.window_seconds
        self._hits[client_ip] = [t for t in self._hits[client_ip] if t > window_start]

        if len(self._hits[client_ip]) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
            )

        self._hits[client_ip].append(now)
        return await call_next(request)
