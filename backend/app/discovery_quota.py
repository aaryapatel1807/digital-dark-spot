"""Persistent discovery quota + cache (GapLens final stabilization, Part 4).

Why a file, not just memory: the in-memory rate limiter resets on
every restart and does not share state across workers, so it cannot
protect a free-tier quota. This store is a small JSON file under the
backend data directory (path overridable via DISCOVERY_QUOTA_PATH,
so tests can point it at a temp file). It is NOT a database and
NOT cross-worker atomic — two workers could both read-then-write
in the same instant — so it is a conservative, best-effort guard:
limits are deliberately low (global 30/day, per-IP 3/day by
default), cache hits never consume quota, and failures never
consume quota. If the file cannot be written at all, an in-memory
fallback enforces the same limits for the life of the process and
the limitation is documented (see docs/final-stabilization.md).

"Session" here is honestly an IP + calendar-day bucket, not an
authenticated session: GapLens has no accounts, and a browser
identifier would be trivially spoofable. IP buckets are an abuse
control, not authentication, and shared networks will share a
bucket — that tradeoff is stated in the docs.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import date, datetime, timezone
from pathlib import Path

_lock = threading.Lock()
_memory_fallback: dict = {}


def _path() -> Path:
    override = os.environ.get("DISCOVERY_QUOTA_PATH")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[1] / "data" / "discovery_quota.json"


def _load() -> dict:
    try:
        path = _path()
        if path.exists():
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                return data
    except (OSError, ValueError):
        pass
    return dict(_memory_fallback)


def _save(data: dict) -> None:
    try:
        path = _path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
    except OSError:
        _memory_fallback.clear()
        _memory_fallback.update(data)


class QuotaExceeded(Exception):
    pass


def today_key() -> str:
    return date.today().isoformat()


def check_and_record(ip: str, global_limit: int, ip_limit: int) -> None:
    """Atomically (per-process) check limits for today, then record one use."""
    with _lock:
        data = _load()
        if data.get("date") != today_key():
            data = {"date": today_key(), "global": 0, "ips": {}, "cache": data.get("cache", {})}
        if data.get("global", 0) >= global_limit:
            raise QuotaExceeded(
                f"Discovery daily limit reached ({global_limit} searches today). Try again tomorrow, or add website links / documents instead."
            )
        ips = data.setdefault("ips", {})
        if ips.get(ip, 0) >= ip_limit:
            raise QuotaExceeded(
                f"Discovery limit reached for today ({ip_limit} searches). Add website links or documents instead."
            )
        data["global"] = data.get("global", 0) + 1
        ips[ip] = ips.get(ip, 0) + 1
        _save(data)


def get_cached(query: str, ttl_seconds: int) -> tuple[list, str] | None:
    with _lock:
        data = _load()
        entry = data.get("cache", {}).get(query)
        if not entry:
            return None
        try:
            retrieved = datetime.fromisoformat(entry["retrieved_at"])
        except (KeyError, ValueError):
            return None
        age = (datetime.now(timezone.utc) - retrieved).total_seconds()
        if age > ttl_seconds:
            return None
        return entry["results"], entry["retrieved_at"]


def set_cached(query: str, results: list) -> None:
    with _lock:
        data = _load()
        cache = data.setdefault("cache", {})
        cache[query] = {
            "results": results,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }
        # Keep the cache bounded: drop oldest entries beyond 200.
        while len(cache) > 200:
            oldest = min(cache, key=lambda k: cache[k]["retrieved_at"])
            del cache[oldest]
        _save(data)


def normalize_query(query: str) -> str:
    import re

    return re.sub(r"\s+", " ", query.strip().lower())
