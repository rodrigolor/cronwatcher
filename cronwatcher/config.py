"""Configuration loader for cronwatcher."""

import os
from dataclasses import dataclass, field
from typing import List, Optional

import yaml


@dataclass
class JobConfig:
    name: str
    schedule: str
    command: str
    timeout: int = 300
    alert_on_failure: bool = True
    alert_on_missed: bool = True
    notify_channels: List[str] = field(default_factory=list)


@dataclass
class AlertConfig:
    email: Optional[str] = None
    slack_webhook: Optional[str] = None
    pagerduty_key: Optional[str] = None


@dataclass
class CronWatcherConfig:
    jobs: List[JobConfig]
    alerts: AlertConfig
    log_level: str = "INFO"
    state_file: str = "/var/lib/cronwatcher/state.json"
    check_interval: int = 60


def load_config(path: str) -> CronWatcherConfig:
    """Load and validate configuration from a YAML file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError("Invalid config: root must be a mapping")

    alert_raw = raw.get("alerts", {})
    alerts = AlertConfig(
        email=alert_raw.get("email"),
        slack_webhook=alert_raw.get("slack_webhook"),
        pagerduty_key=alert_raw.get("pagerduty_key"),
    )

    jobs = []
    for job_raw in raw.get("jobs", []):
        if "name" not in job_raw or "schedule" not in job_raw or "command" not in job_raw:
            raise ValueError(f"Job missing required fields: {job_raw}")
        jobs.append(
            JobConfig(
                name=job_raw["name"],
                schedule=job_raw["schedule"],
                command=job_raw["command"],
                timeout=job_raw.get("timeout", 300),
                alert_on_failure=job_raw.get("alert_on_failure", True),
                alert_on_missed=job_raw.get("alert_on_missed", True),
                notify_channels=job_raw.get("notify_channels", []),
            )
        )

    return CronWatcherConfig(
        jobs=jobs,
        alerts=alerts,
        log_level=raw.get("log_level", "INFO"),
        state_file=raw.get("state_file", "/var/lib/cronwatcher/state.json"),
        check_interval=raw.get("check_interval", 60),
    )
