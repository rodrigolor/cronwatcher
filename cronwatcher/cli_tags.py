"""CLI sub-commands for inspecting job tags."""
from __future__ import annotations

import argparse
import sys

from cronwatcher.config import CronWatcherConfig
from cronwatcher.tags import TagRegistry


def _build_registry(config: CronWatcherConfig) -> TagRegistry:
    registry = TagRegistry()
    for job in config.jobs:
        registry.register(job.name, getattr(job, "tags", []) or [])
    return registry


def cmd_tags_list(args: argparse.Namespace, config: CronWatcherConfig) -> int:
    """List all known tags and the jobs associated with each."""
    registry = _build_registry(config)
    tags = sorted(registry.all_tags())
    if not tags:
        print("No tags defined.")
        return 0
    for tag in tags:
        jobs = sorted(registry.jobs_for_tag(tag))
        print(f"{tag}: {', '.join(jobs)}")
    return 0


def cmd_tags_filter(args: argparse.Namespace, config: CronWatcherConfig) -> int:
    """Print job names that match the given tag(s)."""
    registry = _build_registry(config)
    all_jobs = [job.name for job in config.jobs]
    matched = sorted(registry.filter_jobs(all_jobs, args.tags))
    if not matched:
        print("No jobs match the specified tag(s).")
        return 1
    for name in matched:
        print(name)
    return 0


def build_tags_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    tags_parser = subparsers.add_parser("tags", help="Inspect job tags")
    tag_sub = tags_parser.add_subparsers(dest="tags_cmd", required=True)

    tag_sub.add_parser("list", help="List all tags and their jobs")

    filter_p = tag_sub.add_parser("filter", help="Filter jobs by tag")
    filter_p.add_argument(
        "tags",
        nargs="+",
        metavar="TAG",
        help="One or more tags to filter by",
    )
