"""In-process request performance metrics for the Security hub's
"Cybersecurity — Performance & Quality" panel.

Aggregates since process start (resets on restart/deploy — that's the right
window for an ops dashboard, not a historical time-series store). Recorded
via app.py's before/after_request hooks on every non-static request.
"""
import threading
import time
from collections import deque

_lock = threading.Lock()
_start_time = time.time()
_count = 0
_total_ms = 0.0
_status_4xx = 0
_status_5xx = 0
_recent_ms = deque(maxlen=500)  # bounded sample for p95/max, not full history


def record(duration_ms, status_code):
    global _count, _total_ms, _status_4xx, _status_5xx
    with _lock:
        _count += 1
        _total_ms += duration_ms
        _recent_ms.append(duration_ms)
        if 400 <= status_code < 500:
            _status_4xx += 1
        elif status_code >= 500:
            _status_5xx += 1


def snapshot():
    with _lock:
        count = _count
        total_ms = _total_ms
        status_4xx = _status_4xx
        status_5xx = _status_5xx
        recent = sorted(_recent_ms)

    avg_ms = (total_ms / count) if count else 0.0
    p95_ms = recent[int(len(recent) * 0.95) - 1] if recent else 0.0
    max_ms = recent[-1] if recent else 0.0
    error_count = status_4xx + status_5xx
    error_rate_pct = (error_count / count * 100) if count else 0.0

    return {
        "uptime_seconds": round(time.time() - _start_time),
        "requests_served": count,
        "avg_response_ms": round(avg_ms, 1),
        "p95_response_ms": round(p95_ms, 1),
        "max_response_ms": round(max_ms, 1),
        "error_rate_pct": round(error_rate_pct, 2),
        "status_4xx_count": status_4xx,
        "status_5xx_count": status_5xx,
    }
