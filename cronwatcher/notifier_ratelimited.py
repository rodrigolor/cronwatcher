"""Notifier wrapper that applies rate limiting before forwarding alerts."""
from __future__ import annotations

import logging
from typing import Optional

from cronwatcher.notifier import Notifier
from cronwatcher.ratelimit import RateLimiter, RateLimitPolicy

logger = logging.getLogger(__name__)


class RateLimitedNotifier:
    """Wraps a Notifier and suppresses alerts that exceed the rate limit."""

    def __init__(
        self,
        inner: Notifier,
        policy: RateLimitPolicy,
        limiter: Optional[RateLimiter] = None,
    ) -> None:
        self._inner = inner
        self._limiter = limiter or RateLimiter(policy)

    def notify_missed(self, job_name: str) -> None:
        if self._limiter.is_allowed(job_name):
            self._inner.notify_missed(job_name)
        else:
            logger.debug(
                "Rate limit suppressed missed alert for job '%s'", job_name
            )

    def notify_failure(self, job_name: str, exit_code: int) -> None:
        if self._limiter.is_allowed(job_name):
            self._inner.notify_failure(job_name, exit_code)
        else:
            logger.debug(
                "Rate limit suppressed failure alert for job '%s' (exit=%d)",
                job_name,
                exit_code,
            )

    def recover(self, job_name: str) -> None:
        """Reset rate limit state when a job recovers."""
        self._limiter.reset(job_name)
        if hasattr(self._inner, "recover"):
            self._inner.recover(job_name)  # type: ignore[union-attr]
