"""CLI sub-command: cronwatcher forecast — show predicted next run times."""

from __future__ import annotations

import argparse
import json
from datetime import timezone
from typing import List

from cronwatcher.config import CronWatcherConfig
from cronwatcher.forecast import Forecaster, ForecastEntry
from cronwatcher.scheduler import Scheduler


def _build_scheduler(cfg: CronWatcherConfig) -> Scheduler:
    s = Scheduler()
    for job in cfg.jobs:
        s.register(job)
    return s


def _render_text(entries: List[ForecastEntry]) -> str:
    if not entries:
        return "No jobs registered."
    lines = [f"{'JOB':<30} {'NEXT RUN (UTC)':<26} {'OVERDUE?'}",
             "-" * 70]
    for e in entries:
        overdue_str = f"YES (+{e.overdue_by_seconds:.0f}s)" if e.is_overdue else "no"
        next_str = e.next_run.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"{e.job_name:<30} {next_str:<26} {overdue_str}")
    return "\n".join(lines)


def cmd_forecast(args: argparse.Namespace) -> None:
    cfg = CronWatcherConfig.from_file(args.config)
    scheduler = _build_scheduler(cfg)
    forecaster = Forecaster(cfg.jobs, scheduler)
    entries = forecaster.forecast()

    if args.format == "json":
        print(json.dumps([e.as_dict() for e in entries], indent=2))
    else:
        print(_render_text(entries))


def build_forecast_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("forecast", help="Show predicted next run times for all jobs")
    p.add_argument("--config", default="cronwatcher.yaml", help="Path to config file")
    p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    p.set_defaults(func=cmd_forecast)
