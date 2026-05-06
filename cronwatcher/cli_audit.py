"""CLI sub-commands for inspecting the cronwatcher audit log."""
from __future__ import annotations

import argparse
from pathlib import Path

from cronwatcher.audit import AuditLog


def cmd_audit_list(args: argparse.Namespace) -> None:
    """Print audit events, optionally filtered by job or event type."""
    log = AuditLog(args.log_dir)
    events = log.read_all()

    if args.job:
        events = [e for e in events if e.job_name == args.job]
    if args.event_type:
        events = [e for e in events if e.event_type == args.event_type]
    if args.last:
        events = events[-args.last :]

    if not events:
        print("No audit events found.")
        return

    col_w = 22
    header = f"{'TIMESTAMP':<{col_w}}  {'TYPE':<20}  {'JOB':<24}  DETAIL"
    print(header)
    print("-" * len(header))
    for ev in events:
        ts = ev.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        job = ev.job_name or "-"
        print(f"{ts:<{col_w}}  {ev.event_type:<20}  {job:<24}  {ev.detail}")


def build_audit_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p: argparse.ArgumentParser = subparsers.add_parser(
        "audit", help="Inspect the cronwatcher audit log"
    )
    p.add_argument(
        "--log-dir",
        default="/var/lib/cronwatcher",
        help="Directory that contains audit.jsonl (default: /var/lib/cronwatcher)",
    )
    p.add_argument("--job", default=None, help="Filter by job name")
    p.add_argument("--event-type", default=None, help="Filter by event type")
    p.add_argument(
        "--last",
        type=int,
        default=None,
        metavar="N",
        help="Show only the last N events",
    )
    p.set_defaults(func=cmd_audit_list)
