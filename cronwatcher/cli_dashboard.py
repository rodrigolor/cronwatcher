"""CLI sub-command: cronwatcher status."""
from __future__ import annotations

import argparse
import sys

from cronwatcher.config import CronWatcherConfig, load_config
from cronwatcher.dashboard import Dashboard
from cronwatcher.history import HistoryStore
from cronwatcher.scheduler import Scheduler


def cmd_status(args: argparse.Namespace) -> int:
    """Print a live status dashboard to stdout."""
    try:
        cfg: CronWatcherConfig = load_config(args.config)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    store = HistoryStore(cfg.history_dir)
    scheduler = Scheduler()
    for job in cfg.jobs:
        scheduler.register(job)

    # Seed last_seen from the most recent history record so the dashboard
    # reflects persisted state even when the daemon is not running.
    for job in cfg.jobs:
        records = store.read_for_job(job.name)
        if records:
            latest = max(records, key=lambda r: r.timestamp)
            state = scheduler.states.get(job.name)
            if state and (state.last_seen is None or latest.timestamp > state.last_seen):
                state.last_seen = latest.timestamp

    dashboard = Dashboard(scheduler, store)
    print(dashboard.render(), end="")
    return 0


def build_status_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "status",
        help="Show a summary dashboard of all monitored cron jobs.",
    )
    p.add_argument(
        "--config",
        default="cronwatcher.yaml",
        help="Path to configuration file (default: cronwatcher.yaml).",
    )
    p.set_defaults(func=cmd_status)
