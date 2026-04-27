"""Configuration loading and validation for cronwatcher."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class JobConfig:
    name: str
    schedule: str          # cron expression, e.g. "*/5 * * * *"
    grace_seconds: int = 60


@dataclass
class AlertConfig:
    enabled: bool = True
    log_level: str = "WARNING"
    email_recipients: list[str] = field(default_factory=list)
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_from: str = "cronwatcher@localhost"


@dataclass
class CronWatcherConfig:
    jobs: list[JobConfig]
    alerts: AlertConfig = field(default_factory=AlertConfig)
    poll_interval: float = 30.0


def _parse_alert(raw: dict[str, Any]) -> AlertConfig:
    return AlertConfig(
        enabled=bool(raw.get("enabled", True)),
        log_level=str(raw.get("log_level", "WARNING")),
        email_recipients=list(raw.get("email_recipients", [])),
        smtp_host=str(raw.get("smtp_host", "localhost")),
        smtp_port=int(raw.get("smtp_port", 25)),
        smtp_from=str(raw.get("smtp_from", "cronwatcher@localhost")),
    )


def _parse_job(raw: dict[str, Any]) -> JobConfig:
    if "name" not in raw:
        raise ValueError("Job entry missing required field 'name'.")
    if "schedule" not in raw:
        raise ValueError(f"Job '{raw['name']}' missing required field 'schedule'.")
    return JobConfig(
        name=str(raw["name"]),
        schedule=str(raw["schedule"]),
        grace_seconds=int(raw.get("grace_seconds", 60)),
    )


def load_config(path: str | Path) -> CronWatcherConfig:
    """Load and parse a YAML configuration file."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open() as fh:
        raw = yaml.safe_load(fh) or {}

    jobs_raw = raw.get("jobs", [])
    if not isinstance(jobs_raw, list):
        raise ValueError("'jobs' must be a list.")

    jobs = [_parse_job(j) for j in jobs_raw]
    alerts = _parse_alert(raw.get("alerts", {}))
    poll_interval = float(raw.get("poll_interval", 30.0))

    return CronWatcherConfig(jobs=jobs, alerts=alerts, poll_interval=poll_interval)
