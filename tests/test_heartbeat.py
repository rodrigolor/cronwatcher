"""Tests for the HeartbeatServer HTTP ping receiver."""

from __future__ import annotations

import threading
import time
import urllib.request
from http.client import HTTPResponse
from typing import List

import pytest

from cronwatcher.heartbeat import HeartbeatServer


def _free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture()
def server():
    port = _free_port()
    received: List[str] = []
    srv = HeartbeatServer("127.0.0.1", port, received.append)
    srv.start()
    time.sleep(0.05)  # give thread a moment
    yield srv, port, received
    srv.stop()


def _get(port: int, path: str) -> tuple[int, str]:
    url = f"http://127.0.0.1:{port}{path}"
    with urllib.request.urlopen(url, timeout=2) as resp:  # type: HTTPResponse
        return resp.status, resp.read().decode()


def test_ping_valid_job(server):
    srv, port, received = server
    status, body = _get(port, "/ping/daily_backup")
    assert status == 200
    assert "daily_backup" in body
    assert received == ["daily_backup"]


def test_ping_multiple_jobs(server):
    srv, port, received = server
    _get(port, "/ping/job_a")
    _get(port, "/ping/job_b")
    assert received == ["job_a", "job_b"]


def test_unknown_path_returns_404(server):
    srv, port, received = server
    try:
        _get(port, "/unknown/route")
        assert False, "Expected HTTPError"
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
    assert received == []


def test_stop_joins_thread(server):
    srv, port, received = server
    srv.stop()
    assert not srv._thread.is_alive()
