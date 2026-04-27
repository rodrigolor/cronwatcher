"""Core watcher daemon: ties scheduler, notifier, and history together."""

from __future__ import annotations

import logging
import time
from typing import Optional

from cronwatcher.config import CronWatcherConfig
from cronwatcher.history import ExecutionRecord, HistoryStore
from cronwatcher.notifier import Notifier
from cronwatcher.scheduler import Scheduler

logger = logging.getLogger(__name__)


class Watcher:
    """Orchestrates periodic checks and dispatches alerts."""

    def __init__(
        self,
        config: CronWatcherConfig,
        scheduler: Optional[Scheduler] = None,
        notifier: Optional[Notifier] = None,
        history: Optional[HistoryStore] = None,
    ) -> None:
        self._config = config
        self._scheduler = scheduler or Scheduler()
        self._notifier = notifier or Notifier(config.alerts)
        self._history: Optional[HistoryStore] = history
        self._running = False

        for job in config.jobs:
            self._scheduler.register(job)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_job_result(
        self,
        job_name: str,
        success: bool,
        exit_code: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        """Record a job execution result in the scheduler and history."""
        self._scheduler.record_execution(job_name)
        if self._history is not None:
            entry = ExecutionRecord.now(
                job_name=job_name,
                success=success,
                exit_code=exit_code,
                message=message,
            )
            self._history.record(entry)
        if not success:
            self._notifier.notify_failure(job_name, exit_code=exit_code, message=message)

    def tick(self) -> None:
        """Check for missed jobs and dispatch alerts."""
        missed = self._scheduler.check_missed()
        for job_name in missed:
            logger.info("Missed job detected: %s", job_name)
            self._notifier.notify_missed(job_name)

    def run(self, interval: float = 60.0) -> None:
        """Run the watcher loop until stop() is called."""
        self._running = True
        logger.info("Watcher started (interval=%.1fs)", interval)
        while self._running:
            self.tick()
            time.sleep(interval)
        logger.info("Watcher stopped")

    def stop(self) -> None:
        """Signal the run loop to exit."""
        self._running = False
