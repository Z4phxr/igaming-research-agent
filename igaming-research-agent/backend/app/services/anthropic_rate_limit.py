"""Client-side request-rate limiting for Anthropic Haiku analyzer calls.

Keeps automated pipeline runs under typical request-rate limits by spacing
requests and retrying HTTP 429 responses with backoff.

This limiter does not estimate or enforce token-per-minute usage.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_WINDOW_SECONDS = 60.0


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    logger.warning(
        "Unrecognized boolean value for %s: %r. Falling back to default=%s.",
        name,
        raw,
        default,
    )
    return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class AnthropicRateLimiter:
    """Thread-safe sliding-window limiter with a minimum inter-request gap."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        max_requests_per_minute: int = 45,
        min_interval_seconds: float = 1.3,
        max_retries: int = 5,
        retry_base_seconds: float = 2.0,
        window_seconds: float = _WINDOW_SECONDS,
    ) -> None:
        self.enabled = enabled
        self.max_requests_per_minute = max(1, max_requests_per_minute)
        self.min_interval_seconds = max(0.0, min_interval_seconds)
        self.max_retries = max(0, max_retries)
        self.retry_base_seconds = max(0.1, retry_base_seconds)
        self.window_seconds = max(0.1, window_seconds)

        self._lock = threading.Lock()
        self._request_times: deque[float] = deque()
        self._last_request_at = 0.0

    def _compute_wait_seconds(self, now: float) -> float:
        while self._request_times and now - self._request_times[0] >= self.window_seconds:
            self._request_times.popleft()

        waits: list[float] = []

        if len(self._request_times) >= self.max_requests_per_minute:
            oldest = self._request_times[0]
            waits.append(self.window_seconds - (now - oldest) + 0.05)

        if self._last_request_at > 0 and self.min_interval_seconds > 0:
            elapsed = now - self._last_request_at
            if elapsed < self.min_interval_seconds:
                waits.append(self.min_interval_seconds - elapsed)

        return max(waits) if waits else 0.0

    def acquire(self) -> None:
        if not self.enabled:
            return

        while True:
            wait_seconds = 0.0
            with self._lock:
                now = time.monotonic()
                wait_seconds = self._compute_wait_seconds(now)
                if wait_seconds <= 0:
                    self._request_times.append(now)
                    self._last_request_at = now
                    return

            logger.debug("Haiku rate limiter sleeping %.2fs", wait_seconds)
            time.sleep(wait_seconds)

    def run_with_retry(self, operation: Callable[[], T], *, operation_name: str = "anthropic_call") -> T:
        """Acquire a slot, run the API call, and retry on rate-limit errors."""
        if not self.enabled:
            return operation()

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self.acquire()
            try:
                return operation()
            except Exception as exc:
                if not is_rate_limit_error(exc) or attempt >= self.max_retries:
                    raise
                last_error = exc
                backoff = self.retry_base_seconds * (2**attempt)
                logger.warning(
                    "%s rate limited (attempt %s/%s); retrying in %.1fs",
                    operation_name,
                    attempt + 1,
                    self.max_retries,
                    backoff,
                )
                time.sleep(backoff)

        assert last_error is not None
        raise last_error


def is_rate_limit_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True

    error_type = getattr(exc, "type", None)
    if isinstance(error_type, str) and "rate_limit" in error_type.lower():
        return True

    message = str(exc).lower()
    return "rate_limit" in message or "rate limit" in message or "429" in message


_haiku_rate_limiter: AnthropicRateLimiter | None = None
_limiter_lock = threading.Lock()


def get_haiku_rate_limiter() -> AnthropicRateLimiter:
    global _haiku_rate_limiter
    if _haiku_rate_limiter is not None:
        return _haiku_rate_limiter

    with _limiter_lock:
        if _haiku_rate_limiter is None:
            _haiku_rate_limiter = AnthropicRateLimiter(
                enabled=_env_bool("ANTHROPIC_HAIKU_RATE_LIMIT_ENABLED", True),
                max_requests_per_minute=_env_int("ANTHROPIC_HAIKU_MAX_RPM", 45),
                min_interval_seconds=_env_float("ANTHROPIC_HAIKU_MIN_REQUEST_INTERVAL_SECONDS", 1.3),
                max_retries=_env_int("ANTHROPIC_HAIKU_MAX_RETRIES", 5),
                retry_base_seconds=_env_float("ANTHROPIC_HAIKU_RETRY_BASE_SECONDS", 2.0),
            )
        return _haiku_rate_limiter


def reset_haiku_rate_limiter_for_tests() -> None:
    """Clear the process-wide limiter singleton (test helper)."""
    global _haiku_rate_limiter
    with _limiter_lock:
        _haiku_rate_limiter = None
