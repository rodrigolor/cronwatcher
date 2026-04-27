"""Alert dispatching for cronwatcher."""

from __future__ import annotations

import logging
import smtplib
from abc import ABC, abstractmethod
from email.message import EmailMessage
from typing import Optional

from cronwatcher.config import AlertConfig

logger = logging.getLogger(__name__)


class AlertBackend(ABC):
    """Abstract base class for alert backends."""

    @abstractmethod
    def send(self, subject: str, body: str) -> None:
        """Send an alert message."""


class LogAlertBackend(AlertBackend):
    """Logs alerts using Python's logging module (useful for testing/dev)."""

    def send(self, subject: str, body: str) -> None:
        logger.warning("ALERT — %s: %s", subject, body)


class EmailAlertBackend(AlertBackend):
    """Sends alerts via SMTP email."""

    def __init__(self, config: AlertConfig) -> None:
        self.config = config

    def send(self, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.config.from_address
        msg["To"] = ", ".join(self.config.recipients)
        msg.set_content(body)

        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as smtp:
                if self.config.smtp_tls:
                    smtp.starttls()
                if self.config.smtp_user and self.config.smtp_password:
                    smtp.login(self.config.smtp_user, self.config.smtp_password)
                smtp.send_message(msg)
            logger.info("Alert email sent: %s", subject)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send alert email: %s", exc)


class AlertDispatcher:
    """Dispatches alerts through one or more backends."""

    def __init__(self, backends: list[AlertBackend]) -> None:
        self.backends = backends

    def dispatch(self, subject: str, body: str) -> None:
        for backend in self.backends:
            backend.send(subject, body)


def build_dispatcher(config: Optional[AlertConfig]) -> AlertDispatcher:
    """Build an AlertDispatcher from configuration."""
    backends: list[AlertBackend] = [LogAlertBackend()]
    if config and config.enabled and config.recipients:
        backends.append(EmailAlertBackend(config))
    return AlertDispatcher(backends)
