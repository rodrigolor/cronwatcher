"""CLI sub-command: show duration trend analysis for monitored jobs."""
from __future__ import annotations

import argparse
from pathlib import Path

from cronwatcher.config import CronWatcherConfig
from cronwatcher.history import HistoryStore
from cronwatcher.trending import TrendAnalyzer, TrendPolicy


def _build_analyzer(args: argparse.Namespace) -> tuple[TrendAnalyzer, list[str]]:
    cfg = CronWatcherConfig.from_file(args.config)
    store = HistoryStore(Path(args.history_dir or "./cronwatcher_history"))
    policy = TrendPolicy(
        min_samples=args.min_samples,
        degradation_slope_threshold=args.slope_threshold,
    )
    analyzer = TrendAnalyzer(store, policy)
    job_names = [j.name for j in cfg.jobs]
    return analyzer, job_names


def cmd_trending(args: argparse.Namespace) -> None:
    analyzer, job_names = _build_analyzer(args)
    results = analyzer.analyze_all(job_names)

    if not results:
        print("No trend data available (insufficient samples).")
        return

    print(f"{'JOB':<30} {'STATUS':<12} {'MEAN(s)':>8} {'SLOPE':>9} {'N':>5}")
    print("-" * 68)
    for r in results:
        status = "DEGRADING" if r.is_degrading else "ok"
        print(
            f"{r.job_name:<30} {status:<12} "
            f"{r.mean_duration:>8.1f} {r.slope:>+9.3f} {r.sample_count:>5}"
        )


def build_trending_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("trending", help="Show execution duration trends")
    p.add_argument("--config", default="cronwatcher.yaml", help="Config file path")
    p.add_argument("--history-dir", default=None, help="History directory")
    p.add_argument(
        "--min-samples", type=int, default=5,
        help="Minimum samples required for trend analysis",
    )
    p.add_argument(
        "--slope-threshold", type=float, default=1.0,
        help="Slope (s/run) above which a job is flagged as degrading",
    )
    p.set_defaults(func=cmd_trending)
