"""Persistent LLM metrics history.

Flushes per-minute delta buckets from MetricsStore to the `llm_metrics_buckets`
table every 60 seconds so stats survive container restarts.

Exposes `query_history(range_key)` which returns bucketed time-series data for
the g-hub monitor dashboard.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import text

logger = logging.getLogger(__name__)

_FLUSH_INTERVAL = 60  # seconds

_RANGE_CONFIGS: Dict[str, Dict[str, Any]] = {
    # range_key: cutoff_hours, bucket_secs (used in raw epoch arithmetic)
    "1d":  {"cutoff_hours": 24,    "bucket_secs": 900},    # 15-min buckets → 96 pts
    "7d":  {"cutoff_hours": 24*7,  "bucket_secs": 3600},   # 1-hour buckets → 168 pts
    "30d": {"cutoff_hours": 24*30, "bucket_secs": 21600},  # 6-hour buckets → 120 pts
}


class HistoryFlusher:
    """Asyncio background task that writes per-minute metric deltas to the DB."""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop(), name="metrics-history-flush")

    async def stop(self, timeout: float = 5.0) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._task), timeout=timeout)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(_FLUSH_INTERVAL)
            await _flush_once()


async def _flush_once() -> None:
    from llm_api.observability.metrics import get_metrics_store
    delta = get_metrics_store().flush_delta()
    if not delta["requests"] and not delta["errors"]:
        return
    try:
        await asyncio.to_thread(_write_bucket, delta)
    except Exception as exc:
        logger.warning("metrics history flush failed: %s", exc)


def _bucket_now() -> datetime:
    """Current UTC time truncated to the minute."""
    now = datetime.now(timezone.utc)
    return now.replace(second=0, microsecond=0)


def _write_bucket(delta: Dict[str, Any]) -> None:
    """Upsert one minute bucket into llm_metrics_buckets (runs in thread pool)."""
    from llm_api.db.database import get_engine
    engine = get_engine()
    if engine is None:
        return

    bt = _bucket_now()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT requests, errors, fallbacks, total_latency_ms, "
                "latency_count, provider_counts "
                "FROM llm_metrics_buckets WHERE bucket_time = :bt"
            ),
            {"bt": bt},
        ).fetchone()

        if row:
            # Merge provider counts at the Python level to avoid JSON operator
            # differences between PostgreSQL and SQLite.
            merged: Dict[str, int] = dict(row.provider_counts or {})
            for k, v in delta["provider_counts"].items():
                merged[k] = merged.get(k, 0) + int(v)
            conn.execute(
                text("""
                    UPDATE llm_metrics_buckets
                    SET requests          = requests + :req,
                        errors            = errors + :err,
                        fallbacks         = fallbacks + :fb,
                        total_latency_ms  = total_latency_ms + :tlat,
                        latency_count     = latency_count + :lc,
                        provider_counts   = :pc
                    WHERE bucket_time = :bt
                """),
                {
                    "req": delta["requests"],
                    "err": delta["errors"],
                    "fb": delta["fallbacks"],
                    "tlat": delta["total_latency_ms"],
                    "lc": delta["latency_count"],
                    "pc": merged,
                    "bt": bt,
                },
            )
        else:
            conn.execute(
                text("""
                    INSERT INTO llm_metrics_buckets
                        (bucket_time, requests, errors, fallbacks,
                         total_latency_ms, latency_count, provider_counts)
                    VALUES (:bt, :req, :err, :fb, :tlat, :lc, :pc)
                """),
                {
                    "bt": bt,
                    "req": delta["requests"],
                    "err": delta["errors"],
                    "fb": delta["fallbacks"],
                    "tlat": delta["total_latency_ms"],
                    "lc": delta["latency_count"],
                    "pc": delta["provider_counts"],
                },
            )


def query_history(range_key: str = "1d") -> Dict[str, Any]:
    """Query bucketed history from DB.  Requires PostgreSQL (returns empty for SQLite)."""
    from llm_api.db.database import get_engine
    engine = get_engine()

    empty = {
        "range": range_key,
        "buckets": [],
        "totals": {"requests": 0, "errors": 0, "fallbacks": 0, "avg_latency_ms": 0.0},
    }

    if engine is None or engine.dialect.name != "postgresql":
        return empty

    cfg = _RANGE_CONFIGS.get(range_key, _RANGE_CONFIGS["1d"])
    cutoff = datetime.now(timezone.utc) - timedelta(hours=cfg["cutoff_hours"])
    bs = int(cfg["bucket_secs"])  # safe: from hardcoded config dict, not user input

    # Epoch-floor bucketing works across all PostgreSQL versions.
    sql = text(f"""
        SELECT
            to_timestamp(floor(extract(epoch from bucket_time) / {bs}) * {bs})
                ::timestamptz AS ts,
            SUM(requests)         AS requests,
            SUM(errors)           AS errors,
            SUM(fallbacks)        AS fallbacks,
            SUM(total_latency_ms) AS total_lat,
            SUM(latency_count)    AS lat_count
        FROM llm_metrics_buckets
        WHERE bucket_time >= :cutoff
        GROUP BY 1
        ORDER BY 1
    """)

    try:
        with engine.connect() as conn:
            rows = conn.execute(sql, {"cutoff": cutoff}).fetchall()
    except Exception as exc:
        logger.warning("query_history failed: %s", exc)
        return empty

    buckets: List[Dict[str, Any]] = []
    total_req = total_err = total_fb = total_lc = 0
    total_lat = 0.0

    for row in rows:
        req = int(row.requests or 0)
        err = int(row.errors or 0)
        fb = int(row.fallbacks or 0)
        tlat = float(row.total_lat or 0.0)
        lc = int(row.lat_count or 0)
        avg_lat = round(tlat / lc, 1) if lc else 0.0
        buckets.append({
            "ts": row.ts.isoformat(),
            "requests": req,
            "errors": err,
            "fallbacks": fb,
            "avg_latency_ms": avg_lat,
        })
        total_req += req
        total_err += err
        total_fb += fb
        total_lat += tlat
        total_lc += lc

    return {
        "range": range_key,
        "buckets": buckets,
        "totals": {
            "requests": total_req,
            "errors": total_err,
            "fallbacks": total_fb,
            "avg_latency_ms": round(total_lat / total_lc, 1) if total_lc else 0.0,
        },
    }
