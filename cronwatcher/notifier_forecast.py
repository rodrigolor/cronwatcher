"""Notifier wrapper that attaches forecast context to missed-job alerts."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from cronwatcher.forecast import Forecaster
from cronwatcher.notifier import Notifier

logger = logging.getLogger(__name__)


class ForecastingNotifier:
    """Wraps a Notifier and enriches missed-job messages with forecast data."""

    def __init__(self, inner: Notifier, forecaster: Forecaster) -> None:
        self._inner = inner
        self._forecaster = forecaster

    def notify_missed(self, job_name: str, last_seen: Optional[datetime] = None) -> None:
        entries = {e.job_name: e for e in self._forecaster.forecast()}
        entry = entries.get(job_name)
        if entry is not None:
            overdue_s = entry.overdue_by_seconds
            next_iso = entry.next_run.isoformat()
            logger.info(
                "Forecast context for missed job %r: next_run=%s overdue_by=%.1fs",
                job_name,
                next_iso,
                overdue_s,
            )
        self._inner.notify_missed(job_name, last_seen)

    def notify_failure(
        self,
        job_name: str,
        exit_code: int,
        output: str = "",
        last_seen: Optional[datetime] = None,
    ) -> None:
        self._inner.notify_failure(job_name, exit_code, output, last_seen)

    def recover(self, job_name: str) -> None:
        if hasattr(self._inner, "recover"):
            self._inner.recover(job_name)  # type: ignore[attr-defined]
