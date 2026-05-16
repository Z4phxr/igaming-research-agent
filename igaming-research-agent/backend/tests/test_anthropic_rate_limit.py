import time

import pytest

from app.services import anthropic_rate_limit as rate_limit


@pytest.fixture(autouse=True)
def reset_limiter():
    rate_limit.reset_haiku_rate_limiter_for_tests()
    yield
    rate_limit.reset_haiku_rate_limiter_for_tests()


def test_acquire_enforces_minimum_interval():
    limiter = rate_limit.AnthropicRateLimiter(
        enabled=True,
        max_requests_per_minute=1000,
        min_interval_seconds=0.2,
        max_retries=0,
    )

    limiter.acquire()
    start = time.monotonic()
    limiter.acquire()
    elapsed = time.monotonic() - start

    assert elapsed >= 0.18


def test_acquire_enforces_rpm_window():
    limiter = rate_limit.AnthropicRateLimiter(
        enabled=True,
        max_requests_per_minute=2,
        min_interval_seconds=0.0,
        max_retries=0,
        window_seconds=0.15,
    )

    limiter.acquire()
    limiter.acquire()
    start = time.monotonic()
    limiter.acquire()
    elapsed = time.monotonic() - start

    assert elapsed >= 0.1
    assert elapsed < 1.0


def test_run_with_retry_on_rate_limit(monkeypatch):
    limiter = rate_limit.AnthropicRateLimiter(
        enabled=True,
        max_requests_per_minute=1000,
        min_interval_seconds=0.0,
        max_retries=2,
        retry_base_seconds=0.01,
    )
    attempts = {"count": 0}

    class RateLimitedError(Exception):
        status_code = 429

    def flaky_call():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RateLimitedError("rate_limit_error")
        return "ok"

    result = limiter.run_with_retry(flaky_call, operation_name="test_call")

    assert result == "ok"
    assert attempts["count"] == 3


def test_env_bool_falls_back_to_default_on_unrecognized_value(monkeypatch):
    monkeypatch.setenv("TEST_BOOL_FLAG", "treu")
    assert rate_limit._env_bool("TEST_BOOL_FLAG", True) is True
    assert rate_limit._env_bool("TEST_BOOL_FLAG", False) is False


def test_env_bool_parses_explicit_false(monkeypatch):
    monkeypatch.setenv("TEST_BOOL_FLAG", "false")
    assert rate_limit._env_bool("TEST_BOOL_FLAG", True) is False


def test_is_rate_limit_error_detects_status_code():
    class Err(Exception):
        status_code = 429

    assert rate_limit.is_rate_limit_error(Err("too many requests")) is True
    assert rate_limit.is_rate_limit_error(Exception("other")) is False
