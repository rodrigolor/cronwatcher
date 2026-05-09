"""CLI commands for job duration profiling."""
from __future__ import annotations

import argparse
import sys

from cronwatcher.history import HistoryStore
from cronwatcher.profiling import JobProfiler, ProfilingPolicy


def _build_profiler(args: argparse.Namespace) -> JobProfiler:
    store = HistoryStore(args.history_dir)
    policy = ProfilingPolicy(min_samples=args.min_samples)
    return JobProfiler(store, policy)


def cmd_profile(args: argparse.Namespace) -> None:
    profiler = _build_profiler(args)
    if args.job:
        profile = profiler.profile(args.job)
        if profile is None:
            print(
                f"Not enough samples for '{args.job}' "
                f"(need at least {args.min_samples})."
            )
        else:
            print(profile)
    else:
        store = HistoryStore(args.history_dir)
        job_names = list({r.job_name for r in store.read_all()})
        profiles = profiler.profile_all(job_names)
        if not profiles:
            print("No profiling data available.")
            return
        for name in sorted(profiles):
            print(profiles[name])


def build_profiling_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("profile", help="Show execution duration profiles")
    p.add_argument(
        "--history-dir",
        default=".cronwatcher/history",
        help="Path to history directory",
    )
    p.add_argument(
        "--job",
        default=None,
        help="Profile a single job (omit for all jobs)",
    )
    p.add_argument(
        "--min-samples",
        type=int,
        default=5,
        help="Minimum samples required to compute a profile",
    )
    p.set_defaults(func=cmd_profile)
