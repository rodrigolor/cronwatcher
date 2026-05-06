"""CLI sub-command: cronwatcher anomaly  — report duration anomalies."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronwatcher.anomaly import AnomalyDetector, AnomalyPolicy
from cronwatcher.config import CronWatcherConfig
from cronwatcher.history import HistoryStore


def cmd_anomaly(args: argparse.Namespace) -> None:
    cfg = CronWatcherConfig.load(args.config)
    store = HistoryStore(Path(args.history_dir or cfg.history_dir))

    policy = AnomalyPolicy(
        min_samples=args.min_samples,
        threshold=args.threshold,
    )
    detector = AnomalyDetector(store=store, policy=policy)

    if args.job:
        durations = detector._durations(args.job)
        if not durations:
            print(f"No duration data for job '{args.job}'.")
            return
        results = [detector.check(args.job, d) for d in durations]
        flagged = [r for r in results if r.is_anomaly]
    else:
        flagged_map = detector.scan_all()
        flagged = [r for results in flagged_map.values() for r in results]

    if not flagged:
        print("No anomalies detected.")
        return

    print(f"{'JOB':<30} {'DURATION':>10} {'MEAN':>10} {'STDDEV':>10} {'Z-SCORE':>9}")
    print("-" * 75)
    for r in sorted(flagged, key=lambda x: (x.job_name, -(x.z_score or 0))):
        print(
            f"{r.job_name:<30} {r.duration:>10.2f} {r.mean:>10.2f}"
            f" {r.stddev:>10.2f} {r.z_score:>9.2f}"
        )
    sys.exit(1 if flagged else 0)


def build_anomaly_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("anomaly", help="Report duration anomalies for cron jobs")
    p.add_argument("--config", default="cronwatcher.yaml", help="Path to config file")
    p.add_argument("--history-dir", default=None, help="Override history directory")
    p.add_argument("--job", default=None, help="Limit scan to a single job")
    p.add_argument(
        "--min-samples", type=int, default=5,
        help="Minimum number of samples required to detect anomalies (default: 5)",
    )
    p.add_argument(
        "--threshold", type=float, default=3.0,
        help="Z-score threshold for anomaly (default: 3.0)",
    )
    p.set_defaults(func=cmd_anomaly)
