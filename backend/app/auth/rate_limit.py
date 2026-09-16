"""Login abuse protection (11_SECURITY_DESIGN section 3, 10 section 13).

Deliberately in-process and dependency-free: the MVP runs a single backend
process, so a fixed-window counter in memory is the smallest thing that
actually works. No Redis, no new infrastructure.

Only FAILED attempts are counted and a successful login clears the counter,
so ordinary use — including a user mistyping a password once or twice, and
automated test suites logging in repeatedly with valid credentials — is never
throttled. The key pairs the client address with the submitted email so one
attacker cannot lock out an unrelated account from a different address.

Known limits, stated rather than hidden: counters reset when the process
restarts and are not shared across workers. Deployments that run multiple
workers or need durable throttling should move this behind a shared store or
the edge proxy.
"""
from __future__ import annotations

import time
from collections import defaultdict


class LoginRateLimiter:
    def __init__(self, max_attempts: int = 10, window_seconds: int = 300) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _prune(self, key: str, now: float) -> list[float]:
        recent = [t for t in self._hits[key] if now - t < self.window_seconds]
        self._hits[key] = recent
        return recent

    def is_blocked(self, key: str) -> bool:
        return len(self._prune(key, time.monotonic())) >= self.max_attempts

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        self._prune(key, now)
        self._hits[key].append(now)

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)

    def clear(self) -> None:
        self._hits.clear()


_limiter: LoginRateLimiter | None = None


def get_login_limiter() -> LoginRateLimiter:
    global _limiter
    if _limiter is None:
        from ..config import get_settings

        settings = get_settings()
        _limiter = LoginRateLimiter(
            max_attempts=settings.login_max_attempts,
            window_seconds=settings.login_window_seconds,
        )
    return _limiter


def login_key(client_host: str | None, email: str) -> str:
    return f"{client_host or 'unknown'}|{email.strip().lower()}"
