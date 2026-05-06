"""CLI sub-commands for inspecting runbook entries."""
from __future__ import annotations

import argparse
import sys
from typing import Optional

from cronwatcher.config import CronWatcherConfig
from cronwatcher.runbook import RunbookRegistry, build_registry_from_config


def _build_registry(config: CronWatcherConfig) -> RunbookRegistry:
    raw_jobs = [
        {"name": j.name, "runbook": getattr(j, "runbook", None)}
        for j in config.jobs
    ]
    return build_registry_from_config(raw_jobs)


def cmd_runbook_show(args: argparse.Namespace) -> int:
    config = CronWatcherConfig.from_file(args.config)
    registry = _build_registry(config)

    job_name: Optional[str] = args.job
    if job_name:
        entry = registry.get(job_name)
        if entry is None:
            print(f"No runbook found for job '{job_name}'.", file=sys.stderr)
            return 1
        print(entry.summary())
        return 0

    jobs = registry.all_jobs()
    if not jobs:
        print("No runbook entries registered.")
        return 0
    for name in jobs:
        entry = registry.get(name)
        if entry:
            print(entry.summary())
            print()
    return 0


def build_runbook_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("runbook", help="Show runbook entries for jobs")
    p.add_argument(
        "--config",
        default="cronwatcher.yaml",
        help="Path to configuration file",
    )
    p.add_argument(
        "--job",
        default=None,
        metavar="JOB_NAME",
        help="Show runbook for a specific job only",
    )
    p.set_defaults(func=cmd_runbook_show)
