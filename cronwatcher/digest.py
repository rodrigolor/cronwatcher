"""Periodic digest report sender for cronwatcher."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from cronwatcher.notifier import Notifier
from cronwatcher.report import Report, ReportGenerator
from cronwatcher.history import HistoryStore
from cronwatcher.config import CronWatcherConfig

logger = logging.getLogger(__name__)


class DigestSender:
    """Sends a periodic digest of job execution summaries via the notifier."""

    def __init__(
        self,
        config: CronWatcherConfig,
        store: HistoryStore,
        notifier: Notifier,
        interval_seconds: int = 86400,
    ) -> None:
        self._config = config
        self._store = store
        self._notifier = notifier
        self._interval = interval_seconds
        self._last_sent: Optional[datetime] = None

    def _is_due(self, now: datetime) -> bool:
        if self._last_sent is None:
            return True
        elapsed = (now - self._last_sent).total_seconds()
        return elapsed >= self._interval

    def _build_report(self) -> Report:
        generator = ReportGenerator(self._store)
        job_names = [job.name for job in self._config.jobs]
        return generator.generate(job_names)

    def maybe_send(self, now: Optional[datetime] = None) -> bool:
        """Send digest if interval has elapsed. Returns True if sent."""
        if now is None:
            now = datetime.now(timezone.utc)

        if not self._is_due(now):
            return False

        report = self._build_report()
        text = report.as_text()
        logger.info("Sending digest report")
        self._notifier.notify_digest(text)
        self._last_sent = now
        return True
