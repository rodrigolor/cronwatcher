"""CLI sub-commands for snapshot management."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cronwatcher.snapshots import SnapshotManager
from cronwatcher.config import CronWatcherConfig
from cronwatcher.scheduler import Scheduler


def _build_scheduler(cfg: CronWatcherConfig) -> Scheduler:
    scheduler = Scheduler()
    for job in cfg.jobs:
        scheduler.register(job)
    return scheduler


def cmd_snapshot_capture(args: argparse.Namespace) -> None:
    cfg = CronWatcherConfig.load(args.config)
    scheduler = _build_scheduler(cfg)
    manager = SnapshotManager(Path(args.snapshot_dir))
    snapshot = manager.capture(scheduler)
    print(f"Snapshot captured at {snapshot.captured_at} with {len(snapshot.entries)} job(s).")
    for entry in snapshot.entries:
        status = "MISSED" if entry.missed else "OK"
        last = entry.last_seen or "never"
        print(f"  {entry.job_name:<30} {status:<8} last_seen={last}")


def cmd_snapshot_list(args: argparse.Namespace) -> None:
    manager = SnapshotManager(Path(args.snapshot_dir))
    files = manager.list_snapshots()
    if not files:
        print("No snapshots found.")
        return
    for f in files:
        print(f.name)


def cmd_snapshot_diff(args: argparse.Namespace) -> None:
    manager = SnapshotManager(Path(args.snapshot_dir))
    files = manager.list_snapshots()
    if len(files) < 2:
        print("Need at least two snapshots to diff.")
        return
    import json as _json
    a = manager.load_latest.__func__  # avoid calling; load by index
    snap_a = __import__('cronwatcher.snapshots', fromlist=['Snapshot']).Snapshot.from_dict(
        _json.loads(files[-2].read_text())
    )
    snap_b = __import__('cronwatcher.snapshots', fromlist=['Snapshot']).Snapshot.from_dict(
        _json.loads(files[-1].read_text())
    )
    diff = manager.diff(snap_a, snap_b)
    if not diff:
        print("No changes between last two snapshots.")
        return
    print(f"Changes between {files[-2].name} and {files[-1].name}:")
    print(json.dumps(diff, indent=2))


def build_snapshot_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("snapshot", help="Manage scheduler snapshots")
    p.add_argument("--snapshot-dir", default=".cronwatcher/snapshots", metavar="DIR")
    sub = p.add_subparsers(dest="snapshot_cmd", required=True)

    cap = sub.add_parser("capture", help="Capture current scheduler state")
    cap.add_argument("--config", default="cronwatcher.yaml")
    cap.set_defaults(func=cmd_snapshot_capture)

    lst = sub.add_parser("list", help="List existing snapshots")
    lst.set_defaults(func=cmd_snapshot_list)

    dif = sub.add_parser("diff", help="Diff last two snapshots")
    dif.set_defaults(func=cmd_snapshot_diff)
