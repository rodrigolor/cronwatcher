"""Circuit breaker for alert backends — suppresses repeated alerts when a
backend is consistently failing to avoid alert storms."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CircuitBreakerPolicy:
    failure_threshold: int = 3   # consecutive failures before opening
    recovery_timeout: float = 60.0  # seconds before attempting half-open

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be positive")


class _State:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class _BreakerState:
    state: str = _State.CLOSED
    consecutive_failures: int = 0
    opened_at: Optional[datetime] = None


class CircuitBreaker:
    """Wraps an alert backend call and trips open on repeated failures."""

    def __init__(self, policy: Optional[CircuitBreakerPolicy] = None) -> None:
        self._policy = policy or CircuitBreakerPolicy()
        self._states: dict[str, _BreakerState] = {}

    def _get(self, backend_id: str) -> _BreakerState:
        if backend_id not in self._states:
            self._states[backend_id] = _BreakerState()
        return self._states[backend_id]

    def is_allowed(self, backend_id: str) -> bool:
        """Return True if the backend should be called right now."""
        st = self._get(backend_id)
        if st.state == _State.CLOSED:
            return True
        if st.state == _State.OPEN:
            elapsed = (_utcnow() - st.opened_at).total_seconds()  # type: ignore[operator]
            if elapsed >= self._policy.recovery_timeout:
                st.state = _State.HALF_OPEN
                logger.info("CircuitBreaker[%s] -> HALF_OPEN", backend_id)
                return True
            return False
        # HALF_OPEN: allow one probe
        return True

    def record_success(self, backend_id: str) -> None:
        st = self._get(backend_id)
        if st.state != _State.CLOSED:
            logger.info("CircuitBreaker[%s] -> CLOSED (recovered)", backend_id)
        st.state = _State.CLOSED
        st.consecutive_failures = 0
        st.opened_at = None

    def record_failure(self, backend_id: str) -> None:
        st = self._get(backend_id)
        st.consecutive_failures += 1
        if st.state == _State.HALF_OPEN or st.consecutive_failures >= self._policy.failure_threshold:
            st.state = _State.OPEN
            st.opened_at = _utcnow()
            logger.warning(
                "CircuitBreaker[%s] -> OPEN after %d failure(s)",
                backend_id,
                st.consecutive_failures,
            )

    def state_for(self, backend_id: str) -> str:
        return self._get(backend_id).state
