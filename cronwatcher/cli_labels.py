"""CLI commands for managing job labels."""
from __future__ import annotations

import argparse

from cronwatcher.labels import LabelStore

# Module-level singleton so commands share state within a process.
_store = LabelStore()


def _build_store() -> LabelStore:  # pragma: no cover – seam for tests
    return _store


def cmd_labels_set(args: argparse.Namespace) -> None:
    store = _build_store()
    store.set(args.job, args.key, args.value)
    print(f"Label set: {args.job}  {args.key}={args.value}")


def cmd_labels_get(args: argparse.Namespace) -> None:
    store = _build_store()
    value = store.get(args.job, args.key)
    if value is None:
        print(f"No label '{args.key}' for job '{args.job}'")
    else:
        print(f"{args.key}={value}")


def cmd_labels_show(args: argparse.Namespace) -> None:
    store = _build_store()
    labels = store.get_all(args.job)
    if not labels:
        print(f"No labels for job '{args.job}'")
    else:
        for k, v in sorted(labels.items()):
            print(f"  {k}={v}")


def cmd_labels_remove(args: argparse.Namespace) -> None:
    store = _build_store()
    store.remove(args.job, args.key)
    print(f"Label '{args.key}' removed from job '{args.job}'")


def cmd_labels_filter(args: argparse.Namespace) -> None:
    store = _build_store()
    jobs = store.jobs_with_label(args.key, args.value)
    if not jobs:
        print("No jobs match.")
    else:
        for j in jobs:
            print(j)


def build_labels_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("labels", help="Manage job labels")
    sub = p.add_subparsers(dest="labels_cmd", required=True)

    ps = sub.add_parser("set", help="Set a label on a job")
    ps.add_argument("job")
    ps.add_argument("key")
    ps.add_argument("value")
    ps.set_defaults(func=cmd_labels_set)

    pg = sub.add_parser("get", help="Get a label value")
    pg.add_argument("job")
    pg.add_argument("key")
    pg.set_defaults(func=cmd_labels_get)

    psh = sub.add_parser("show", help="Show all labels for a job")
    psh.add_argument("job")
    psh.set_defaults(func=cmd_labels_show)

    pr = sub.add_parser("remove", help="Remove a label from a job")
    pr.add_argument("job")
    pr.add_argument("key")
    pr.set_defaults(func=cmd_labels_remove)

    pf = sub.add_parser("filter", help="List jobs matching a label")
    pf.add_argument("key")
    pf.add_argument("value", nargs="?", default=None)
    pf.set_defaults(func=cmd_labels_filter)
