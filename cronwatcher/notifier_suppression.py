"""Notifier wrapper that skips alerts for suppressed jobs."""
from __future__ import annotations

import logging
from typing import Optional

from cronwatcher.notifier import Notifier
from cronwatcher.suppression import SuppressionRegistry

logger = logging.getLogger(__name__)


class SuppressingNotifier:
    """Wraps an inner :class:`Notifier` and silences it for suppressed jobs.

    Example usage::

        registry = SuppressionRegistry()
        registry.add(SuppressionRule("backup", expires_at=..., reason="maintenance"))
        notifier = SuppressingNotifier(inner=real_notifier, registry=registry)
        notifier.notify_missed("backup")   # silently dropped
    """

    def __init__(self, inner: Notifier, registry: SuppressionRegistry) -> None:
        self._inner = inner
        self._registry = registry

    def notify_missed(self, job_name: str) -> None:
        if self._registry.is_suppressed(job_name):
            logger.debug("notify_missed suppressed for job %r", job_name)
            return
        self._inner.notify_missed(job_name)

    def notify_failure(self, job_name: str, detail: Optional[str] = None) -> None:
        if self._registry.is_suppressed(job_name):
            logger.debug("notify_failure suppressed for job %r", job_name)
            return
        self._inner.notify_failure(job_name, detail)

    def recover(self, job_name: str) -> None:
        """Forward recovery signal regardless of suppression."""
        if hasattr(self._inner, "recover"):
            self._inner.recover(job_name)  # type: ignore[union-attr]
