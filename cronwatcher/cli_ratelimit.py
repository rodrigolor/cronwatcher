"""CLI sub-command to display rate-limit status for monitored jobs."""
from __future__ import annotations

import argparse
from typing import Optional

from cronwatcher.ratelimit import RateLimiter, RateLimitPolicy

_HEADER = f"{'JOB':<30} {'ALLOWED':<10} {'SUPPRESSED':<12}"
_SEP = "-" * 54


def cmd_ratelimit_status(
    args: argparse.Namespace,
    limiter: Optional[RateLimiter] = None,
) -> None:
    """Print current rate-limit counters for all tracked jobs."""
    if limiter is None:
        print("No rate limiter active.")
        return

    states = limiter._states  # intentional internal access for diagnostics
    if not states:
        print("No rate-limit state recorded yet.")
        return

    print(_HEADER)
    print(_SEP)
    for job_name, state in sorted(states.items()):
        policy = limiter._policy
        allowed = min(state.count, policy.max_alerts)
        suppressed = limiter.suppressed_count(job_name)
        print(f"{job_name:<30} {allowed:<10} {suppressed:<12}")


def build_ratelimit_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "ratelimit-status",
        help="Show rate-limit counters for all monitored jobs",
    )
    p.set_defaults(func=cmd_ratelimit_status)
