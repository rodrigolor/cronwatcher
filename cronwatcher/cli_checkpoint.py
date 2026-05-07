"""CLI commands for inspecting and managing job checkpoints."""
from __future__ import annotations

import argparse
from pathlib import Path

from cronwatcher.checkpoint import CheckpointStore


def _build_store(args: argparse.Namespace) -> CheckpointStore:
    return CheckpointStore(Path(args.checkpoint_file))


def cmd_checkpoint_list(args: argparse.Namespace) -> None:
    store = _build_store(args)
    entries = store.all_entries()
    if not entries:
        print("No checkpoints recorded.")
        return
    print(f"{'Job':<30} {'Last Success':<30} {'Runs':>6}")
    print("-" * 68)
    for e in entries:
        print(f"{e.job_name:<30} {e.last_success.isoformat():<30} {e.run_count:>6}")


def cmd_checkpoint_show(args: argparse.Namespace) -> None:
    store = _build_store(args)
    entry = store.get(args.job)
    if entry is None:
        print(f"No checkpoint found for job '{args.job}'.")
        return
    print(f"Job       : {entry.job_name}")
    print(f"Last OK   : {entry.last_success.isoformat()}")
    print(f"Run count : {entry.run_count}")


def cmd_checkpoint_clear(args: argparse.Namespace) -> None:
    store = _build_store(args)
    removed = store.clear(args.job)
    if removed:
        print(f"Checkpoint for '{args.job}' cleared.")
    else:
        print(f"No checkpoint found for '{args.job}'.")


def build_checkpoint_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("checkpoint", help="Manage job checkpoints")
    p.add_argument(
        "--checkpoint-file",
        default=".cronwatcher_checkpoints.json",
        help="Path to checkpoint store (default: .cronwatcher_checkpoints.json)",
    )
    sub = p.add_subparsers(dest="checkpoint_cmd", required=True)

    sub.add_parser("list", help="List all checkpoints").set_defaults(func=cmd_checkpoint_list)

    show_p = sub.add_parser("show", help="Show checkpoint for a specific job")
    show_p.add_argument("job", help="Job name")
    show_p.set_defaults(func=cmd_checkpoint_show)

    clear_p = sub.add_parser("clear", help="Remove checkpoint for a specific job")
    clear_p.add_argument("job", help="Job name")
    clear_p.set_defaults(func=cmd_checkpoint_clear)
