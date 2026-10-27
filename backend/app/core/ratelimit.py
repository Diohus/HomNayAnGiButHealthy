"""Giới hạn tần suất in-memory (cửa sổ trượt), thread-safe, không cần dependency ngoài.

Giả định: chạy **một instance** backend (xem docs/ASSUMPTIONS.md). Nhiều instance/worker ⇒ mỗi tiến trình
đếm riêng; khi đó cần chuyển sang kho dùng chung (Redis...).
"""

import math
import threading
import time
from collections import deque

from fastapi import Request

from app.core.errors import AppError

# (số lần, cửa sổ giây)
LOGIN_FAILURES = (5, 15 * 60)  # theo (email, IP); chỉ đếm lần sai
LOGIN_FAILURES_IP = (30, 15 * 60)  # theo IP, mọi email (chống credential stuffing); chỉ đếm lần sai
REGISTER = (10, 60 * 60)  # theo IP
CHAT = (20, 60)  # theo user
RECIPE = (10, 60)  # theo user
MAX_WINDOW_S = max(w for _, w in (LOGIN_FAILURES, LOGIN_FAILURES_IP, REGISTER, CHAT, RECIPE))
MAX_KEYS = 10_000


class RateLimiter:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _window(self, key: str, window_s: float, now: float) -> deque[float]:
        q = self._hits.setdefault(key, deque())
        while q and q[0] <= now - window_s:
            q.popleft()
        return q

    def retry_after(self, key: str, limit: int, window_s: float) -> int | None:
        """Số giây phải chờ nếu đã chạm ngưỡng, None nếu còn được phép. Không ghi nhận lượt mới."""
        with self._lock:
            now = self._clock()
            q = self._window(key, window_s, now)
            if len(q) < limit:
                if not q:
                    self._hits.pop(key, None)
                return None
            return max(1, math.ceil(q[0] + window_s - now))

    def record(self, key: str) -> None:
        with self._lock:
            self._sweep()
            self._hits.setdefault(key, deque()).append(self._clock())

    def _sweep(self) -> None:
        """Chặn bộ nhớ phình theo số khóa: bỏ khóa không có lượt nào trong cửa sổ dài nhất."""
        if len(self._hits) < MAX_KEYS:
            return
        cutoff = self._clock() - MAX_WINDOW_S
        for k in [k for k, q in self._hits.items() if not q or q[-1] <= cutoff]:
            del self._hits[k]

    def hit(self, key: str, limit: int, window_s: float) -> None:
        """Kiểm tra và ghi nhận một lượt; vượt ngưỡng ⇒ AppError 429 (lượt bị chặn không được tính)."""
        with self._lock:
            now = self._clock()
            q = self._window(key, window_s, now)
            if len(q) >= limit:
                raise_limited(max(1, math.ceil(q[0] + window_s - now)))
            self._sweep()
            self._hits.setdefault(key, q).append(now)

    def clear(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def raise_limited(retry_after_s: int):
    raise AppError(429, "RATE_LIMITED", params={"retry_after_s": retry_after_s}, retry_after_s=retry_after_s)


def client_ip(request: Request) -> str:
    # Sau Caddy/nginx, uvicorn chạy --proxy-headers nên request.client là IP thật của người dùng
    return request.client.host if request.client else "unknown"


limiter = RateLimiter()
