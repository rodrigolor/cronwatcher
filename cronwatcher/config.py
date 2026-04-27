"""Configuration loading for cronwatcher."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class JobConfig:
    name: str
    schedule: str
    grace_period: int = 60  # seconds
    command: Optional[str] = None


@dataclass
class AlertConfig:
    enabled: bool = False
    recipients: List[str] = field(default_factory=list)
    from_address: str = "cronwatcher@localhost"
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_tls: bool = False
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None


@dataclass
class CronWatcherConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    check_interval: int = 60  # seconds
    log_level: str = "INFO"


def _parse_alert(raw: dict) -> AlertConfig:
    return AlertConfig(
        enabled=raw.get("enabled", False),
        recipients=raw.get("recipients", []),
        from_address=raw.get("from_address", "cronwatcher@localhost"),
        smtp_host=raw.get("smtp_host", "localhost"),
        smtp_port=int(raw.get("smtp_port", 25)),
        smtp_tls=raw.get("smtp_tls", False),
        smtp_user=raw.get("smtp_user"),
        smtp_password=raw.get("smtp_password"),
    )


def _parse_job(raw: dict) -> JobConfig:
    return JobConfig(
        name=raw["name"],
        schedule=raw["schedule"],
        grace_period=int(raw.get("grace_period", 60)),
        command=raw.get("command"),
    )


def load_config(path: str | Path) -> CronWatcherConfig:
    """Load and parse a YAML configuration file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")

    with p.open() as fh:
        raw = yaml.safe_load(fh) or {}

    jobs = [_parse_job(j) for j in raw.get("jobs", [])]
    alerts = _parse_alert(raw.get("alerts", {}))

    return CronWatcherConfig(
        jobs=jobs,
        alerts=alerts,
        check_interval=int(raw.get("check_interval", 60)),
        log_level=raw.get("log_level", "INFO"),
    )
