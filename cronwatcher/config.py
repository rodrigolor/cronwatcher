"""Configuration models for cronwatcher."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class AlertConfig:
    enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 25
    from_addr: str = ""
    recipients: List[str] = field(default_factory=list)


@dataclass
class JobConfig:
    name: str
    schedule: str
    grace_seconds: int = 60
    command: Optional[str] = None


@dataclass
class HeartbeatConfig:
    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 8765


@dataclass
class CronWatcherConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    alert: AlertConfig = field(default_factory=AlertConfig)
    heartbeat: HeartbeatConfig = field(default_factory=HeartbeatConfig)
    check_interval: int = 60


def _parse_alert(raw: dict) -> AlertConfig:
    return AlertConfig(
        enabled=raw.get("enabled", False),
        smtp_host=raw.get("smtp_host", "localhost"),
        smtp_port=raw.get("smtp_port", 25),
        from_addr=raw.get("from_addr", ""),
        recipients=raw.get("recipients", []),
    )


def _parse_heartbeat(raw: dict) -> HeartbeatConfig:
    return HeartbeatConfig(
        enabled=raw.get("enabled", False),
        host=raw.get("host", "0.0.0.0"),
        port=raw.get("port", 8765),
    )


def _parse_job(raw: dict) -> JobConfig:
    return JobConfig(
        name=raw["name"],
        schedule=raw["schedule"],
        grace_seconds=raw.get("grace_seconds", 60),
        command=raw.get("command"),
    )


def load_config(path: str | Path) -> CronWatcherConfig:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with p.open() as fh:
        raw = yaml.safe_load(fh) or {}
    return CronWatcherConfig(
        jobs=[_parse_job(j) for j in raw.get("jobs", [])],
        alert=_parse_alert(raw.get("alert", {})),
        heartbeat=_parse_heartbeat(raw.get("heartbeat", {})),
        check_interval=raw.get("check_interval", 60),
    )
