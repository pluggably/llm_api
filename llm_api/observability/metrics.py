from __future__ import annotations

import collections
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List


# ---------------------------------------------------------------------------
# In-memory log buffer
# ---------------------------------------------------------------------------

_LOG_BUFFER_MAX = 500


class _LogBufferHandler(logging.Handler):
    """Captures recent log records into a deque for the /v1/logs endpoint."""

    def __init__(self, maxlen: int = _LOG_BUFFER_MAX) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self._records: collections.deque[dict] = collections.deque(maxlen=maxlen)

    def emit(self, record: logging.LogRecord) -> None:
        try:
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
        # Uvicorn's loggers have propagate=False — attach explicitly so that
        # access logs and server lifecycle messages are also captured.
        for _name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
            logging.getLogger(_name).addHandler(_handler)
    return _handler


@dataclass
class MetricsStore:
    request_count: int = 0
    error_count: int = 0
    fallback_count: int = 0
    latencies_ms: List[float] = field(default_factory=list)
    provider_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def record_request(self) -> None:
        self.request_count += 1

    def record_error(self) -> None:
        self.error_count += 1

    def record_latency(self, latency_ms: float) -> None:
        self.latencies_ms.append(latency_ms)

    def record_provider(self, provider: str, fallback: bool = False) -> None:
        self.provider_counts[provider] += 1
        if fallback:
            self.fallback_count += 1

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
