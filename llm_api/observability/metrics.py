from __future__ import annotations

import collections
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# In-memory log buffer
# ---------------------------------------------------------------------------

_LOG_BUFFER_MAX = 500


_INTERNAL_POLL_PATHS = ("/v1/stats", "/v1/logs", "/v1/history")


class _LogBufferHandler(logging.Handler):
    """Captures recent log records into a deque for the /v1/logs endpoint."""

    def __init__(self, maxlen: int = _LOG_BUFFER_MAX) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self._records: collections.deque[dict] = collections.deque(maxlen=maxlen)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Drop the monitor's own polling noise from the console.
            if record.name == "uvicorn.access":
                msg = record.getMessage()
                if any(p in msg for p in _INTERNAL_POLL_PATHS):
                    return
            entry = {
                "ts": record.created,
                "level": record.levelname,
                "name": record.name,
                "msg": self.format(record),
            }
            with self._lock:
                self._records.append(entry)
        except Exception:
            pass

    def recent(self, n: int = 200) -> list[dict]:
        with self._lock:
            records = list(self._records)
        return records[-n:]


_handler: _LogBufferHandler | None = None


def get_log_handler() -> _LogBufferHandler:
    global _handler
    if _handler is None:
        _handler = _LogBufferHandler()
        _handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
        # Root logger catches all app records that propagate.
        logging.getLogger().addHandler(_handler)
        # Uvicorn loggers: `uvicorn` has propagate=False (add directly),
        # `uvicorn.error` propagates to `uvicorn` so skip it,
        # `uvicorn.access` has propagate=False (add directly).
        for _name in ("uvicorn", "uvicorn.access"):
            logging.getLogger(_name).addHandler(_handler)
    return _handler


@dataclass
class MetricsStore:
    request_count: int = 0
    error_count: int = 0
    fallback_count: int = 0
    latencies_ms: List[float] = field(default_factory=list)
    provider_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def __post_init__(self) -> None:
        # Delta counters: increments since last flush to DB.
        # All reads/writes happen in the single asyncio event loop thread,
        # so no explicit lock is needed for the counters themselves.
        self._delta_requests: int = 0
        self._delta_errors: int = 0
        self._delta_fallbacks: int = 0
        self._delta_latencies: List[float] = []
        self._delta_providers: Dict[str, int] = defaultdict(int)

    def record_request(self) -> None:
        self.request_count += 1
        self._delta_requests += 1

    def record_error(self) -> None:
        self.error_count += 1
        self._delta_errors += 1

    def record_latency(self, latency_ms: float) -> None:
        self.latencies_ms.append(latency_ms)
        self._delta_latencies.append(latency_ms)

    def record_provider(self, provider: str, fallback: bool = False) -> None:
        self.provider_counts[provider] += 1
        self._delta_providers[provider] += 1
        if fallback:
            self.fallback_count += 1
            self._delta_fallbacks += 1

    def flush_delta(self) -> Dict[str, Any]:
        """Return the delta since the last call and atomically reset counters.

        Safe to call from the asyncio event loop — all record_* methods also
        run there, so Python's GIL guarantees consistent snapshots.
        """
        snapshot: Dict[str, Any] = {
            "requests": self._delta_requests,
            "errors": self._delta_errors,
            "fallbacks": self._delta_fallbacks,
            "total_latency_ms": sum(self._delta_latencies),
            "latency_count": len(self._delta_latencies),
            "provider_counts": dict(self._delta_providers),
        }
        self._delta_requests = 0
        self._delta_errors = 0
        self._delta_fallbacks = 0
        self._delta_latencies = []
        self._delta_providers = defaultdict(int)
        return snapshot

    def render_prometheus(self) -> str:
        lines = [
            "# HELP llm_api_request_count Total number of requests",
            "# TYPE llm_api_request_count counter",
            f"llm_api_request_count {self.request_count}",
            "# HELP llm_api_error_count Total number of errors",
            "# TYPE llm_api_error_count counter",
            f"llm_api_error_count {self.error_count}",
            "# HELP llm_api_latency_ms Request latency in milliseconds",
            "# TYPE llm_api_latency_ms summary",
        ]
        if self.latencies_ms:
            lines.append(f"llm_api_latency_ms_count {len(self.latencies_ms)}")
            lines.append(f"llm_api_latency_ms_sum {sum(self.latencies_ms)}")
        else:
            lines.append("llm_api_latency_ms_count 0")
            lines.append("llm_api_latency_ms_sum 0")
        return "\n".join(lines) + "\n"


_store: MetricsStore | None = None


def get_metrics_store() -> MetricsStore:
    global _store
    if _store is None:
        _store = MetricsStore()
    return _store
