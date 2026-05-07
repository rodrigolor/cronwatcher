"""CLI commands for managing job metadata annotations."""
from __future__ import annotations

import argparse
import sys

from cronwatcher.metadata import MetadataStore


def _build_store(args: argparse.Namespace) -> MetadataStore:
    return MetadataStore(directory=args.data_dir)


def cmd_metadata_set(args: argparse.Namespace) -> None:
    store = _build_store(args)
    meta = store.load(args.job)
    meta.set(args.key, args.value)
    store.save(meta)
    print(f"Set '{args.key}' = '{args.value}' on job '{args.job}'")


def cmd_metadata_get(args: argparse.Namespace) -> None:
    store = _build_store(args)
    meta = store.load(args.job)
    value = meta.get(args.key)
    if value is None:
        print(f"Key '{args.key}' not found for job '{args.job}'", file=sys.stderr)
        sys.exit(1)
    print(value)


def cmd_metadata_show(args: argparse.Namespace) -> None:
    store = _build_store(args)
    meta = store.load(args.job)
    if not meta.annotations:
        print(f"No metadata for job '{args.job}'")
        return
    for k, v in sorted(meta.annotations.items()):
        print(f"  {k}: {v}")


def cmd_metadata_remove(args: argparse.Namespace) -> None:
    store = _build_store(args)
    meta = store.load(args.job)
    meta.remove(args.key)
    store.save(meta)
    print(f"Removed key '{args.key}' from job '{args.job}'")


def build_metadata_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("metadata", help="Manage job metadata annotations")
    p.add_argument("--data-dir", default=".cronwatcher/metadata", help="Metadata storage directory")
    sub = p.add_subparsers(dest="metadata_cmd", required=True)

    s = sub.add_parser("set", help="Set a metadata key")
    s.add_argument("job")
    s.add_argument("key")
    s.add_argument("value")
    s.set_defaults(func=cmd_metadata_set)

    g = sub.add_parser("get", help="Get a metadata key")
    g.add_argument("job")
    g.add_argument("key")
    g.set_defaults(func=cmd_metadata_get)

    sh = sub.add_parser("show", help="Show all metadata for a job")
    sh.add_argument("job")
    sh.set_defaults(func=cmd_metadata_show)

    r = sub.add_parser("remove", help="Remove a metadata key")
    r.add_argument("job")
    r.add_argument("key")
    r.set_defaults(func=cmd_metadata_remove)
