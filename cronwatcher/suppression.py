"""Suppression rules: temporarily silence alerts for specific jobs or tags."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SuppressionRule:
    """A rule that suppresses alerts for *job_name* until *expires_at*."""

    job_name: str
    expires_at: datetime
    reason: str = ""

    def is_active(self, now: Optional[datetime] = None) -> bool:
        """Return True if the rule is still in effect."""
        now = now or _utcnow()
        return now < self.expires_at

    def as_dict(self) -> Dict:
        return {
            "job_name": self.job_name,
            "expires_at": self.expires_at.isoformat(),
            "reason": self.reason,
        }


class SuppressionRegistry:
    """Holds active suppression rules and answers is_suppressed queries."""

    def __init__(self) -> None:
        self._rules: List[SuppressionRule] = []

    def add(self, rule: SuppressionRule) -> None:
        """Register a new suppression rule."""
        self._rules.append(rule)
        logger.info(
            "Suppression added for %r until %s (reason: %s)",
            rule.job_name,
            rule.expires_at.isoformat(),
            rule.reason or "<none>",
        )

    def remove_expired(self, now: Optional[datetime] = None) -> int:
        """Drop rules that have passed their expiry.  Returns count removed."""
        now = now or _utcnow()
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.is_active(now)]
        return before - len(self._rules)

    def is_suppressed(self, job_name: str, now: Optional[datetime] = None) -> bool:
        """Return True if *job_name* has at least one active suppression rule."""
        now = now or _utcnow()
        return any(
            r.job_name == job_name and r.is_active(now) for r in self._rules
        )

    def active_rules(self, now: Optional[datetime] = None) -> List[SuppressionRule]:
        """Return all currently active rules."""
        now = now or _utcnow()
        return [r for r in self._rules if r.is_active(now)]
