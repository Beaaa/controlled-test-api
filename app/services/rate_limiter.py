"""
Simple in-memory sliding-window rate limiter.

Tracks requests per IP address. When the limit is exceeded the caller
receives 429 Too Many Requests with a Retry-After header.

This is intentionally simplistic (no Redis, no distributed state) —
it only needs to be good enough for the AI Test Engine to exercise
rate-limit detection and retry logic.
"""

import time
from collections import defaultdict
from threading import Lock

# ── Configuration ─────────────────────────────────────────────────────
RATE_LIMIT = 30          # max requests …
RATE_WINDOW_SECONDS = 60  # … per this many seconds

# ── State ─────────────────────────────────────────────────────────────
_hits: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def _cleanup(key: str, now: float) -> None:
    """Remove timestamps older than the window."""
    cutoff = now - RATE_WINDOW_SECONDS
    _hits[key] = [t for t in _hits[key] if t > cutoff]


def check_rate_limit(client_ip: str) -> dict | None:
    """Return None if the request is allowed, or a dict with error info
    (detail, retry_after) if the limit is exceeded."""
    now = time.time()
    with _lock:
        _cleanup(client_ip, now)
        if len(_hits[client_ip]) >= RATE_LIMIT:
            oldest = _hits[client_ip][0]
            retry_after = int(RATE_WINDOW_SECONDS - (now - oldest)) + 1
            return {
                "detail": "Rate limit exceeded. Try again later.",
                "retry_after": max(retry_after, 1),
            }
        _hits[client_ip].append(now)
    return None
