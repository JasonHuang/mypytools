"""In-process resource boundaries for anonymous public processing jobs."""

from collections import defaultdict, deque
from functools import wraps
import threading
import time

from flask import current_app, request

from ..errors import ApiError


class ProcessingLimiter:
    def __init__(self, capacity):
        self.capacity = capacity
        self._semaphore = threading.BoundedSemaphore(capacity)

    def acquire(self):
        return self._semaphore.acquire(blocking=False)

    def release(self):
        self._semaphore.release()


class RateLimiter:
    def __init__(self, limit, window_seconds):
        self.limit = limit
        self.window_seconds = window_seconds
        self._events = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key, now=None):
        now = time.monotonic() if now is None else now
        cutoff = now - self.window_seconds
        with self._lock:
            if len(self._events) > 4096:
                stale_keys = [
                    event_key
                    for event_key, timestamps in self._events.items()
                    if not timestamps or timestamps[-1] <= cutoff
                ]
                for event_key in stale_keys:
                    self._events.pop(event_key, None)
                while len(self._events) > 8192:
                    self._events.pop(next(iter(self._events)))
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True


def guard_processing_job(view):
    """Fail quickly when an IP or this worker has exhausted its job budget."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        rate_limiter = current_app.extensions["toolmist_rate_limiter"]
        client_key = request.remote_addr or "unknown"
        if not rate_limiter.allow(client_key):
            raise ApiError(
                "RATE_LIMITED",
                "请求过于频繁，请稍后再试",
                429,
            )

        processing = current_app.extensions["toolmist_processing_limiter"]
        if not processing.acquire():
            raise ApiError(
                "SERVER_BUSY",
                "当前处理任务较多，请稍后再试",
                503,
            )
        try:
            return view(*args, **kwargs)
        finally:
            processing.release()

    return wrapped
