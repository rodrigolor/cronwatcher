"""Tests for cronwatcher.silence."""

from datetime import datetime, timedelta, timezone

import pytest

from cronwatcher.silence import SilenceRegistry, SilenceWindow


def _utc(offset_minutes: int = 0) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)


@pytest.fixture()
def registry() -> SilenceRegistry:
    return SilenceRegistry()


def test_active_window_silences_job(registry: SilenceRegistry) -> None:
    window = SilenceWindow(
        job_name="backup",
        start=_utc(-10),
        end=_utc(10),
        reason="maintenance",
    )
    registry.add(window)
    assert registry.is_silenced("backup") is True


def test_expired_window_does_not_silence(registry: SilenceRegistry) -> None:
    window = SilenceWindow(
        job_name="backup",
        start=_utc(-30),
        end=_utc(-5),
    )
    registry.add(window)
    assert registry.is_silenced("backup") is False


def test_future_window_does_not_silence(registry: SilenceRegistry) -> None:
    window = SilenceWindow(
        job_name="backup",
        start=_utc(5),
        end=_utc(30),
    )
    registry.add(window)
    assert registry.is_silenced("backup") is False


def test_unrelated_job_not_silenced(registry: SilenceRegistry) -> None:
    window = SilenceWindow(job_name="backup", start=_utc(-5), end=_utc(5))
    registry.add(window)
    assert registry.is_silenced("report") is False


def test_remove_expired_purges_old_windows(registry: SilenceRegistry) -> None:
    registry.add(SilenceWindow(job_name="a", start=_utc(-20), end=_utc(-1)))
    registry.add(SilenceWindow(job_name="b", start=_utc(-5), end=_utc(5)))
    removed = registry.remove_expired()
    assert removed == 1
    assert registry.is_silenced("b") is True


def test_active_windows_returns_only_current(registry: SilenceRegistry) -> None:
    registry.add(SilenceWindow(job_name="a", start=_utc(-5), end=_utc(5)))
    registry.add(SilenceWindow(job_name="b", start=_utc(10), end=_utc(20)))
    active = registry.active_windows()
    assert len(active) == 1
    assert active[0].job_name == "a"


def test_windows_for_job_returns_all_entries(registry: SilenceRegistry) -> None:
    registry.add(SilenceWindow(job_name="sync", start=_utc(-10), end=_utc(-1)))
    registry.add(SilenceWindow(job_name="sync", start=_utc(1), end=_utc(10)))
    registry.add(SilenceWindow(job_name="other", start=_utc(-5), end=_utc(5)))
    windows = registry.windows_for_job("sync")
    assert len(windows) == 2


def test_is_active_uses_provided_timestamp() -> None:
    fixed = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
    window = SilenceWindow(
        job_name="deploy",
        start=datetime(2024, 6, 1, 11, 0, tzinfo=timezone.utc),
        end=datetime(2024, 6, 1, 13, 0, tzinfo=timezone.utc),
    )
    assert window.is_active(at=fixed) is True
    outside = datetime(2024, 6, 1, 14, 0, tzinfo=timezone.utc)
    assert window.is_active(at=outside) is False
