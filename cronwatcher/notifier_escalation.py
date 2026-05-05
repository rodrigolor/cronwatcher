"""Notifier wrapper that gates alerts through an EscalationManager."""

from __future__ import annotations

from cronwatcher.escalation import EscalationManager, EscalationPolicy
from cronwatcher.notifier import Notifier


class EscalatingNotifier:
    """Wraps a :class:`Notifier` and suppresses repeat alerts during cooldown.

    Typical usage::

        policy = EscalationPolicy(cooldown_minutes=30, max_escalations=5)
        en = EscalatingNotifier(notifier, policy)
        en.notify_missed("backup")   # only fires if not in cooldown
        en.recover("backup")         # clears state when job is healthy again
    """

    def __init__(self, notifier: Notifier, policy: EscalationPolicy) -> None:
        self._notifier = notifier
        self._manager = EscalationManager(policy)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def notify_missed(self, job_name: str) -> bool:
        """Send a missed-job alert if the escalation policy permits.

        Returns True if the alert was forwarded, False if suppressed.
        """
        if not self._manager.should_alert(job_name):
            return False
        self._notifier.notify_missed(job_name)
        self._manager.record_alert(job_name)
        return True

    def notify_failure(self, job_name: str, exit_code: int) -> bool:
        """Send a failure alert if the escalation policy permits.

        Returns True if the alert was forwarded, False if suppressed.
        """
        if not self._manager.should_alert(job_name):
            return False
        self._notifier.notify_failure(job_name, exit_code)
        self._manager.record_alert(job_name)
        return True

    def recover(self, job_name: str) -> None:
        """Clear escalation state when a job recovers successfully."""
        self._manager.clear(job_name)

    def escalation_count(self, job_name: str) -> int:
        """Return the number of escalation alerts sent for *job_name*."""
        return self._manager.escalation_count(job_name)
