"""Tests for cronwatcher.webhook."""
from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock, patch
import urllib.error

import pytest

from cronwatcher.webhook import WebhookAlertBackend, WebhookConfig


@pytest.fixture()
def cfg() -> WebhookConfig:
    return WebhookConfig(url="https://hooks.example.com/alert")


@pytest.fixture()
def backend(cfg: WebhookConfig) -> WebhookAlertBackend:
    return WebhookAlertBackend(cfg)


def _fake_response(status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ---------------------------------------------------------------------------


def test_send_posts_json_payload(backend: WebhookAlertBackend) -> None:
    with patch("urllib.request.urlopen", return_value=_fake_response()) as mock_open:
        backend.send("missed", "backup", "overdue by 10 min")

    mock_open.assert_called_once()
    req = mock_open.call_args[0][0]
    body = json.loads(req.data)
    assert body["event"] == "missed"
    assert body["job"] == "backup"
    assert body["detail"] == "overdue by 10 min"


def test_send_uses_configured_method() -> None:
    cfg = WebhookConfig(url="https://hooks.example.com/alert", method="PUT")
    backend = WebhookAlertBackend(cfg)
    with patch("urllib.request.urlopen", return_value=_fake_response()) as mock_open:
        backend.send("failure", "deploy", "exit code 1")
    req = mock_open.call_args[0][0]
    assert req.method == "PUT"


def test_send_merges_custom_headers() -> None:
    cfg = WebhookConfig(
        url="https://hooks.example.com/alert",
        headers={"X-Token": "secret"},
    )
    backend = WebhookAlertBackend(cfg)
    with patch("urllib.request.urlopen", return_value=_fake_response()) as mock_open:
        backend.send("missed", "sync", "late")
    req = mock_open.call_args[0][0]
    assert req.get_header("X-token") == "secret"
    assert req.get_header("Content-type") == "application/json"


def test_send_skips_event_not_in_filter(backend: WebhookAlertBackend) -> None:
    cfg = WebhookConfig(
        url="https://hooks.example.com/alert",
        events=["failure"],
    )
    backend = WebhookAlertBackend(cfg)
    with patch("urllib.request.urlopen") as mock_open:
        backend.send("missed", "backup", "overdue")
    mock_open.assert_not_called()


def test_send_allows_event_in_filter() -> None:
    cfg = WebhookConfig(
        url="https://hooks.example.com/alert",
        events=["missed", "failure"],
    )
    backend = WebhookAlertBackend(cfg)
    with patch("urllib.request.urlopen", return_value=_fake_response()) as mock_open:
        backend.send("failure", "deploy", "crashed")
    mock_open.assert_called_once()


def test_send_logs_error_on_url_error(backend: WebhookAlertBackend, caplog) -> None:
    import logging

    with caplog.at_level(logging.ERROR, logger="cronwatcher.webhook"):
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            backend.send("missed", "backup", "overdue")

    assert any("connection refused" in r.message for r in caplog.records)
