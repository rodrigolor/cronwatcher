"""Notifier wrapper that enqueues alerts to a dead-letter queue on delivery failure."""
from __future__ import annotations

import logging
from typing import Optional

from cronwatcher.deadletter import DeadLetter, DeadLetterQueue
from cronwatcher.notifier import Notifier

logger = logging.getLogger(__name__)


class DeadLetterNotifier:
    """Wraps an inner Notifier; on exception the alert is saved to the DLQ."""

    def __init__(self, inner: Notifier, queue: DeadLetterQueue) -> None:
        self._inner = inner
        self._queue = queue

    def notify_missed(self, job_name: str) -> None:
        try:
            self._inner.notify_missed(job_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("notify_missed failed for %s, enqueuing: %s", job_name, exc)
            self._queue.push(
                DeadLetter(
                    job_name=job_name,
                    alert_type="missed",
                    message=f"Missed schedule for job '{job_name}'",
                )
            )

    def notify_failure(self, job_name: str, exit_code: Optional[int] = None) -> None:
        try:
            self._inner.notify_failure(job_name, exit_code)
        except Exception as exc:  # noqa: BLE001
            logger.warning("notify_failure failed for %s, enqueuing: %s", job_name, exc)
            self._queue.push(
                DeadLetter(
                    job_name=job_name,
                    alert_type="failure",
                    message=f"Job '{job_name}' failed with exit code {exit_code}",
                )
            )

    def replay(self, max_attempts: int = 3) -> int:
        """Attempt to resend queued alerts; returns number successfully replayed."""
        letters = self._queue.read_all()
        if not letters:
            return 0

        remaining = []
        replayed = 0
        for letter in letters:
            if letter.attempts >= max_attempts:
                logger.error(
                    "Dropping dead letter for %s after %d attempts",
                    letter.job_name,
                    letter.attempts,
                )
                continue
            letter.attempts += 1
            try:
                if letter.alert_type == "missed":
                    self._inner.notify_missed(letter.job_name)
                else:
                    self._inner.notify_failure(letter.job_name)
                replayed += 1
                logger.info("Replayed dead letter for %s", letter.job_name)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Replay failed for %s: %s", letter.job_name, exc)
                remaining.append(letter)

        self._queue.rewrite(remaining)
        return replayed
