"""Main watcher loop: polls cron job heartbeats and triggers alerts on missed/failed jobs."""

import logging
import time
from datetime import datetime, timezone

from cronwatcher.config import CronWatcherConfig
from cronwatcher.notifier import Notifier
from cronwatcher.scheduler import Scheduler

logger = logging.getLogger(__name__)


class Watcher:
    """Orchestrates the scheduler and notifier in a polling loop."""

    def __init__(
        self,
        config: CronWatcherConfig,
        scheduler: Scheduler | None = None,
        notifier: Notifier | None = None,
    ) -> None:
        self.config = config
        self.scheduler = scheduler or Scheduler()
        self.notifier = notifier or Notifier(config.alerts)
        self._running = False

        for job in config.jobs:
            self.scheduler.register(job)
            logger.debug("Registered job '%s'", job.name)

    def tick(self) -> None:
        """Perform a single check cycle: detect missed jobs and fire alerts."""
        now = datetime.now(tz=timezone.utc)
        missed = self.scheduler.check_missed(now)
        for job_name in missed:
            logger.warning("Missed job detected: %s", job_name)
            self.notifier.notify_missed(job_name)

    def run(self, poll_interval: float | None = None) -> None:
        """Block and run the watcher loop until stopped."""
        interval = poll_interval if poll_interval is not None else self.config.poll_interval
        logger.info("Watcher starting (poll_interval=%ss)", interval)
        self._running = True
        try:
            while self._running:
                self.tick()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Watcher interrupted by user.")
        finally:
            self._running = False
            logger.info("Watcher stopped.")

    def stop(self) -> None:
        """Signal the run loop to stop after the current tick."""
        self._running = False
