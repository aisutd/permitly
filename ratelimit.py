"""
ratelimit.py
============
Task B8: a simple per-IP limit, e.g. 20 requests per minute per endpoint.

Use it on any route:   @app.post("/ask", dependencies=[Depends(rate_limit)])

It keeps the counters in memory, which is fine for one server process. If you later run
several workers, each worker counts on its own (the real limit becomes a bit higher).
"""

import time
from collections import defaultdict, deque

from fastapi import Request

import config
from errors import ApiError

WINDOW_SECONDS = 60
_hits: dict[tuple[str, str], deque] = defaultdict(deque)


def client_ip(request: Request) -> str:
    if config.TRUST_PROXY:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(request: Request) -> None:
    key = (client_ip(request), request.url.path)
    now = time.monotonic()
    hits = _hits[key]

    while hits and now - hits[0] > WINDOW_SECONDS:  # forget old requests
        hits.popleft()

    if len(hits) >= config.RATE_LIMIT_PER_MINUTE:
        wait = max(1, int(WINDOW_SECONDS - (now - hits[0])) + 1)
        raise ApiError(
            429, "rate_limited",
            f"Too many requests. Please wait {wait} seconds and try again.",
            headers={"Retry-After": str(wait)},
        )
    hits.append(now)

    if len(_hits) > 10_000:  # safety: do not let the dict grow forever
        for stale in [k for k, v in _hits.items() if not v or now - v[-1] > WINDOW_SECONDS]:
            _hits.pop(stale, None)


def reset() -> None:
    """Used by the tests."""
    _hits.clear()
