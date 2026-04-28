"""CLI entry point for cronwatcher utilities."""

from __future__ import annotations

import argparse
import logging
import sys

from cronwatcher.config import CronWatcherConfig
from cronwatcher.history import HistoryStore
from cronwatcher.retention import RetentionPolicy, RetentionManager

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatcher",
        description="Lightweight cron job monitor",
    )
    sub = parser.add_subparsers(dest="command")

    prune_p = sub.add_parser("prune", help="Prune old history records")
    prune_p.add_argument(
        "--config", required=True, metavar="FILE", help="Path to config YAML"
    )
    prune_p.add_argument(
        "--max-age-days",
        type=int,
        default=None,
        metavar="N",
        help="Override max age in days from config",
    )
    prune_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Report how many records would be pruned without deleting",
    )

    return parser


def cmd_prune(args: argparse.Namespace) -> int:
    cfg = CronWatcherConfig.from_file(args.config)
    store = HistoryStore(cfg.history_dir)

    max_age = args.max_age_days or getattr(cfg, "retention_days", 30)
    policy = RetentionPolicy(max_age_days=max_age)
    manager = RetentionManager(store, policy)

    if args.dry_run:
        all_records = store.read_all()
        expired = sum(1 for r in all_records if policy.is_expired(r))
        print(f"[dry-run] Would prune {expired} record(s) (max_age_days={max_age})")
        return 0

    removed = manager.prune()
    print(f"Pruned {removed} record(s) (max_age_days={max_age})")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "prune":
        return cmd_prune(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
