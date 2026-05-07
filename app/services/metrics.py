"""
Simple in-memory metrics collector.

Tracks per-endpoint and global stats:
  - total request count
  - error count (4xx + 5xx)
  - latency (sum + count for average calculation)
  - per-endpoint breakdown
  - uptime
"""

import time
from collections import defaultdict
from threading import Lock

_lock = Lock()

_start_time: float = time.time()

_total_requests: int = 0
_total_errors: int = 0
_total_latency_ms: float = 0.0

_per_endpoint: dict[str, dict] = defaultdict(
    lambda: {"requests": 0, "errors": 0, "latency_ms": 0.0}
)

_status_code_counts: dict[int, int] = defaultdict(int)


def record_request(method: str, path: str, status_code: int, latency_ms: float) -> None:
    """Record a completed request."""
    global _total_requests, _total_errors, _total_latency_ms

    is_error = status_code >= 400
    key = f"{method} {path}"

    with _lock:
        _total_requests += 1
        _total_latency_ms += latency_ms
        _status_code_counts[status_code] += 1

        if is_error:
            _total_errors += 1

        ep = _per_endpoint[key]
        ep["requests"] += 1
        ep["latency_ms"] += latency_ms
        if is_error:
            ep["errors"] += 1


def get_metrics() -> dict:
    """Return a snapshot of all collected metrics."""
    with _lock:
        avg_latency = (
            round(_total_latency_ms / _total_requests, 2) if _total_requests else 0.0
        )
        uptime_seconds = round(time.time() - _start_time, 1)

        endpoints = {}
        for key, ep in _per_endpoint.items():
            ep_avg = round(ep["latency_ms"] / ep["requests"], 2) if ep["requests"] else 0.0
            endpoints[key] = {
                "requests": ep["requests"],
                "errors": ep["errors"],
                "avg_latency_ms": ep_avg,
            }

        return {
            "uptime_seconds": uptime_seconds,
            "total_requests": _total_requests,
            "total_errors": _total_errors,
            "avg_latency_ms": avg_latency,
            "status_codes": dict(_status_code_counts),
            "endpoints": endpoints,
        }


def reset_metrics() -> None:
    """Reset all counters — useful for testing."""
    global _total_requests, _total_errors, _total_latency_ms, _start_time

    with _lock:
        _total_requests = 0
        _total_errors = 0
        _total_latency_ms = 0.0
        _start_time = time.time()
        _per_endpoint.clear()
        _status_code_counts.clear()
