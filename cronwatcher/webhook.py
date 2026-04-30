"""Webhook alert backend for cronwatcher."""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WebhookConfig:
    url: str
    method: str = "POST"
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: int = 10
    # Optional list of event types to filter: "missed", "failure"
    events: Optional[List[str]] = None


class WebhookAlertBackend:
    """Sends alert payloads to an HTTP webhook endpoint."""

    def __init__(self, config: WebhookConfig) -> None:
        self._cfg = config

    # ------------------------------------------------------------------
    def send(self, event: str, job_name: str, detail: str) -> None:
        """POST a JSON payload to the configured webhook URL.

        Args:
            event:    Event type string, e.g. ``"missed"`` or ``"failure"``.
            job_name: Name of the cron job that triggered the alert.
            detail:   Human-readable description of the problem.
        """
        if self._cfg.events and event not in self._cfg.events:
            logger.debug(
                "webhook: skipping event %r (not in filter %s)",
                event,
                self._cfg.events,
            )
            return

        payload: Dict[str, Any] = {
            "event": event,
            "job": job_name,
            "detail": detail,
        }
        body = json.dumps(payload).encode()

        headers = {"Content-Type": "application/json", **self._cfg.headers}
        req = urllib.request.Request(
            self._cfg.url,
            data=body,
            headers=headers,
            method=self._cfg.method,
        )

        try:
            with urllib.request.urlopen(req, timeout=self._cfg.timeout) as resp:
                status = resp.status
            logger.info(
                "webhook: delivered event=%r job=%r status=%s",
                event,
                job_name,
                status,
            )
        except urllib.error.URLError as exc:
            logger.error(
                "webhook: failed to deliver event=%r job=%r: %s",
                event,
                job_name,
                exc,
            )
