"""High-level notifier that formats and dispatches cronwatcher alerts."""

from __future__ import annotations

import datetime
from typing import Optional

from cronwatcher.alerts import AlertDispatcher
from cronwatcher.scheduler import JobState


class Notifier:
    """Formats alert messages and delegates to AlertDispatcher."""

    def __init__(self, dispatcher: AlertDispatcher) -> None:
        self.dispatcher = dispatcher

    def notify_missed(self, job_name: str, state: JobState, now: Optional[datetime.datetime] = None) -> None:
        """Send an alert for a missed cron job execution."""
        now = now or datetime.datetime.utcnow()
        last_seen = (
            state.last_seen.strftime("%Y-%m-%d %H:%M:%S UTC")
            if state.last_seen
            else "never"
        )
        subject = f"[cronwatcher] Missed job: {job_name}"
        body = (
            f"Job '{job_name}' has missed its scheduled execution.\n"
            f"Schedule   : {state.schedule}\n"
            f"Last seen  : {last_seen}\n"
            f"Checked at : {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        )
        self.dispatcher.dispatch(subject, body)

    def notify_failure(self, job_name: str, exit_code: int, output: str = "") -> None:
        """Send an alert for a job that exited with a non-zero status."""
        subject = f"[cronwatcher] Job failed: {job_name}"
        body = (
            f"Job '{job_name}' finished with exit code {exit_code}.\n"
        )
        if output:
            body += f"\nOutput:\n{output}\n"
        self.dispatcher.dispatch(subject, body)
