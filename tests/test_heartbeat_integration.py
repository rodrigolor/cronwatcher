"""Integration: HeartbeatServer -> Scheduler.record_execution pipeline."""

from __future__ import annotations

import socket
import time
import urllib.request

import pytest

from cronwatcher.heartbeat import HeartbeatServer
from cronwatcher.scheduler import Scheduler
from cronwatcher.config import JobConfig


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture()
def integrated():
    scheduler = Scheduler()
    job = JobConfig(name="sync_job", schedule="* * * * *", grace_seconds=120)
    scheduler.register(job)

    port = _free_port()

    def on_ping(job_name: str) -> None:
        scheduler.record_execution(job_name)

    srv = HeartbeatServer("127.0.0.1", port, on_ping)
    srv.start()
    time.sleep(0.05)
    yield scheduler, srv, port
    srv.stop()


def test_ping_updates_scheduler_last_seen(integrated):
    scheduler, srv, port = integrated
    before = scheduler._states["sync_job"].last_seen
    urllib.request.urlopen(f"http://127.0.0.1:{port}/ping/sync_job", timeout=2)
    after = scheduler._states["sync_job"].last_seen
    assert after is not None
    assert before is None or after > before


def test_ping_unknown_job_does_not_crash(integrated):
    scheduler, srv, port = integrated
    # scheduler has no state for 'ghost_job', record_execution should handle it gracefully
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/ping/ghost_job", timeout=2)
    except Exception:
        pass  # 200 or error — server must not crash
    assert srv._thread.is_alive()
