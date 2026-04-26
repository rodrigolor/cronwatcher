"""Tests for cronwatcher configuration loading."""

import os
import textwrap
import pytest

from cronwatcher.config import load_config, CronWatcherConfig, JobConfig, AlertConfig


MINIMAL_CONFIG = textwrap.dedent("""\
    jobs:
      - name: test-job
        schedule: "* * * * *"
        command: /bin/true
    alerts: {}
""")

FULL_CONFIG = textwrap.dedent("""\
    log_level: DEBUG
    state_file: /tmp/state.json
    check_interval: 30
    alerts:
      email: admin@example.com
      slack_webhook: https://hooks.slack.com/test
    jobs:
      - name: backup
        schedule: "0 2 * * *"
        command: /usr/bin/backup
        timeout: 600
        alert_on_failure: true
        alert_on_missed: false
        notify_channels:
          - email
          - slack
""")


@pytest.fixture
def config_file(tmp_path):
    def _write(content):
        p = tmp_path / "cronwatcher.yaml"
        p.write_text(content)
        return str(p)
    return _write


def test_load_minimal_config(config_file):
    cfg = load_config(config_file(MINIMAL_CONFIG))
    assert isinstance(cfg, CronWatcherConfig)
    assert len(cfg.jobs) == 1
    assert cfg.jobs[0].name == "test-job"
    assert cfg.log_level == "INFO"
    assert cfg.check_interval == 60


def test_load_full_config(config_file):
    cfg = load_config(config_file(FULL_CONFIG))
    assert cfg.log_level == "DEBUG"
    assert cfg.state_file == "/tmp/state.json"
    assert cfg.check_interval == 30
    assert cfg.alerts.email == "admin@example.com"
    assert cfg.alerts.slack_webhook == "https://hooks.slack.com/test"
    job = cfg.jobs[0]
    assert job.name == "backup"
    assert job.timeout == 600
    assert job.alert_on_missed is False
    assert "slack" in job.notify_channels


def test_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/config.yaml")


def test_missing_required_job_field(config_file):
    bad = textwrap.dedent("""\
        jobs:
          - name: incomplete-job
            schedule: "* * * * *"
        alerts: {}
    """)
    with pytest.raises(ValueError, match="missing required fields"):
        load_config(config_file(bad))


def test_invalid_root_type(config_file):
    with pytest.raises(ValueError, match="root must be a mapping"):
        load_config(config_file("- just a list\n"))


def test_default_alert_fields(config_file):
    cfg = load_config(config_file(MINIMAL_CONFIG))
    assert cfg.alerts.email is None
    assert cfg.alerts.slack_webhook is None
    assert cfg.alerts.pagerduty_key is None
