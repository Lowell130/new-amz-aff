"""Dipendenze FastAPI: container, rate limit semplice, protezione admin."""

from __future__ import annotations

import hmac
import time
from collections import defaultdict, deque

from fastapi import Depends, Header, HTTPException, Request, status

from app.core.container import Container


def get_container(request: Request) -> Container:
    return request.app.state.container


class RateLimiter:
    """Rate limit in memoria per IP (sufficiente per un singolo processo; in produzione usare Redis)."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def __call__(self, request: Request, c: Container = Depends(get_container)) -> None:
        limit = c.settings.rate_limit_per_minute
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        q = self._hits[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Troppe richieste, riprova tra poco")
        q.append(now)


rate_limit = RateLimiter()


def require_admin(
    x_admin_token: str | None = Header(default=None), c: Container = Depends(get_container)
) -> None:
    expected = c.settings.admin_token.get_secret_value() if c.settings.admin_token else None
    if not expected or not x_admin_token or not hmac.compare_digest(expected, x_admin_token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Non autorizzato")
