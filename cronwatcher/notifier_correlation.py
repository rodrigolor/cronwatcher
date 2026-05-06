"""Notifier wrapper that adds correlated-failure detection before forwarding alerts."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from cronwatcher.correlation import CorrelationDetector, CorrelationEvent, CorrelationPolicy
from cronwatcher.notifier import Notifier

logger = logging.getLogger(__name__)


class CorrelatingNotifier:
    """Wraps a Notifier and emits an extra log/alert when correlated failures are detected."""

    def __init__(
        self,
        inner: Notifier,
        policy: Optional[CorrelationPolicy] = None,
        detector: Optional[CorrelationDetector] = None,
    ) -> None:
        self._inner = inner
        self._detector = detector or CorrelationDetector(policy or CorrelationPolicy())

    # ------------------------------------------------------------------
    # Public API mirrors Notifier
    # ------------------------------------------------------------------

    def notify_missed(self, job_name: str) -> None:
        self._inner.notify_missed(job_name)
        self._detector.record_failure(job_name)
        self._check_correlation()

    def notify_failure(self, job_name: str, exit_code: int) -> None:
        self._inner.notify_failure(job_name, exit_code)
        self._detector.record_failure(job_name)
        self._check_correlation()

    def recover(self, job_name: str) -> None:
        """Signal that *job_name* has recovered; clears its failure history."""
        self._detector.clear(job_name)
        logger.info("[correlation] job '%s' recovered, failure history cleared", job_name)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _check_correlation(self) -> None:
        events = self._detector.detect()
        for event in events:
            logger.warning("[correlation] %s", event)
