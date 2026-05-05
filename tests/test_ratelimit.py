"""Unit tests for cronwatcher.ratelimit."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from cronwatcher.ratelimit import RateLimitPolicy, RateLimiter


def _utc(offset_seconds: float = 0) -> datetime:
    return datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(
        seconds=offset_seconds
    )


def test_policy_rejects_zero_max_alerts():
    with pytest.raises(ValueError, match="max_alerts"):
        RateLimitPolicy(max_alerts=0, window_seconds=60)


def test_policy_rejects_zero_window():
    with pytest.raises(ValueError, match="window_seconds"):
        RateLimitPolicy(max_alerts=3, window_seconds=0)


def test_first_alert_always_allowed():
    limiter = RateLimiter(RateLimitPolicy(max_alerts=2, window_seconds=60))
    with patch("cronwatcher.ratelimit._utcnow", return_value=_utc(0)):
        assert limiter.is_allowed("job_a") is True


def test_alerts_within_limit_all_allowed():
    limiter = RateLimiter(RateLimitPolicy(max_alerts=3, window_seconds=60))
    with patch("cronwatcher.ratelimit._utcnow", return_value=_utc(0)):
        for _ in range(3):
            assert limiter.is_allowed("job_a") is True


def test_alert_beyond_limit_suppressed():
    limiter = RateLimiter(RateLimitPolicy(max_alerts=2, window_seconds=60))
    with patch("cronwatcher.ratelimit._utcnow", return_value=_utc(0)):
        limiter.is_allowed("job_a")
        limiter.is_allowed("job_a")
        assert limiter.is_allowed("job_a") is False


def test_window_reset_allows_new_alerts():
    limiter = RateLimiter(RateLimitPolicy(max_alerts=1, window_seconds=60))
    with patch("cronwatcher.ratelimit._utcnow", return_value=_utc(0)):
        assert limiter.is_allowed("job_a") is True
        assert limiter.is_allowed("job_a") is False
    # After window expires
    with patch("cronwatcher.ratelimit._utcnow", return_value=_utc(61)):
        assert limiter.is_allowed("job_a") is True


def test_reset_clears_state():
    limiter = RateLimiter(RateLimitPolicy(max_alerts=1, window_seconds=60))
    with patch("cronwatcher.ratelimit._utcnow", return_value=_utc(0)):
        limiter.is_allowed("job_a")
        assert limiter.is_allowed("job_a") is False
        limiter.reset("job_a")
        assert limiter.is_allowed("job_a") is True


def test_different_jobs_tracked_independently():
    limiter = RateLimiter(RateLimitPolicy(max_alerts=1, window_seconds=60))
    with patch("cronwatcher.ratelimit._utcnow", return_value=_utc(0)):
        assert limiter.is_allowed("job_a") is True
        assert limiter.is_allowed("job_a") is False
        assert limiter.is_allowed("job_b") is True


def test_suppressed_count():
    limiter = RateLimiter(RateLimitPolicy(max_alerts=2, window_seconds=60))
    with patch("cronwatcher.ratelimit._utcnow", return_value=_utc(0)):
        for _ in range(5):
            limiter.is_allowed("job_a")
        assert limiter.suppressed_count("job_a") == 3
