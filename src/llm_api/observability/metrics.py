from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import List


@dataclass
class MetricsStore:
    request_count: int = 0
    error_count: int = 0
    latencies_ms: List[float] = field(default_factory=list)

    def record_request(self) -> None:
        self.request_count += 1

    def record_error(self) -> None:
        self.error_count += 1

    def record_latency(self, latency_ms: float) -> None:
        self.latencies_ms.append(latency_ms)

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
