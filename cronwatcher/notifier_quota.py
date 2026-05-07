"""Notifier decorator that suppresses alerts once a job exceeds its quota."""
from __future__ import annotations

import logging
from datetime import datetime

from cronwatcher.notifier import Notifier
from cronwatcher.quota import QuotaManager

logger = logging.getLogger(__name__)


class QuotaEnforcingNotifier:
    """Wraps a :class:`Notifier` and drops alerts that exceed the quota.

    Each alert type (missed / failure) is counted separately per job so that
    a burst of missed alerts cannot exhaust the failure quota.
    """

    def __init__(
        self,
        inner: Notifier,
        missed_quota: QuotaManager,
        failure_quota: QuotaManager,
    ) -> None:
        self._inner = inner
        self._missed = missed_quota
        self._failure = failure_quota

    def notify_missed(self, job_name: str, when: datetime | None = None) -> None:
        if not self._missed.is_allowed(job_name, when):
            logger.debug(
                "quota: suppressing missed alert for '%s' (quota exhausted)", job_name
            )
            return
        self._missed.record_run(job_name, when)
        self._inner.notify_missed(job_name)

    def notify_failure(
        self, job_name: str, exit_code: int, when: datetime | None = None
    ) -> None:
        if not self._failure.is_allowed(job_name, when):
            logger.debug(
                "quota: suppressing failure alert for '%s' (quota exhausted)", job_name
            )
            return
        self._failure.record_run(job_name, when)
        self._inner.notify_failure(job_name, exit_code)

    def recover(self, job_name: str) -> None:
        """Reset quota counters when a job recovers."""
        self._missed.reset(job_name)
        self._failure.reset(job_name)
        if hasattr(self._inner, "recover"):
            self._inner.recover(job_name)  # type: ignore[union-attr]
