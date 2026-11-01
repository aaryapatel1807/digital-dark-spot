"""Source discovery service (GapLens final stabilization, Parts 2–4).

Flow, in order:
1. If discovery is disabled or no provider is configured -> 503
   "not configured" (handled by the endpoint), never invented URLs.
2. Cache hit (normalized query, configurable TTL) -> return cached
   results WITHOUT consuming quota or calling the provider, marked
   cached with their original retrieval timestamp.
3. Quota check (file-backed daily global + per-IP limits) -> if
   exceeded, friendly 503, no provider call, user's input preserved
   by the frontend (it never clears the form on a discovery error).
4. Provider call (SerpApi today, via the provider interface).
   Provider quota errors are detected, NOT retried, and surfaced
   as a structured error; timeouts/failures become 502.
5. Success -> record quota use + cache the results.

Manual URL, pasted-text, and PDF analysis never touch this module
and never require SerpApi: they are the core, discovery is optional.
The key lives server-side only and is never logged or returned.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone

from .config import get_settings
from .discovery_quota import (
    QuotaExceeded,
    check_and_record,
    get_cached,
    normalize_query,
    set_cached,
)
from .search_providers import ProviderError, ProviderQuotaExhausted, SearchProvider, SerpApiProvider

_ENDPOINT = "https://serpapi.com/search.json"
_TIMEOUT_SECONDS = 15.0


class SearchNotConfigured(Exception):
    pass


class SearchFailed(Exception):
    pass


class SearchQuotaExhausted(Exception):
    pass


_query_locks: dict[str, threading.Lock] = {}
_query_locks_guard = threading.Lock()


def _lock_for(query: str) -> threading.Lock:
    with _query_locks_guard:
        return _query_locks.setdefault(query, threading.Lock())


def get_provider() -> SearchProvider:
    """Resolve the configured provider, or raise SearchNotConfigured."""
    settings = get_settings()
    if not settings.discovery_enabled:
        raise SearchNotConfigured(
            "Automatic source discovery is currently unavailable. You can still add website links, paste information, or upload documents."
        )
    provider_name = (settings.search_provider or "serpapi").lower()
    if provider_name == "none":
        raise SearchNotConfigured(
            "Automatic source discovery is currently unavailable. You can still add website links, paste information, or upload documents."
        )
    if provider_name == "serpapi":
        if not settings.search_api_key:
            raise SearchNotConfigured(
                "Automatic source discovery is currently unavailable. You can still add website links, paste information, or upload documents."
            )
        return SerpApiProvider(settings.search_api_key)
    raise SearchNotConfigured(f"Unknown search provider '{provider_name}'. Discovery is unavailable.")


def discover_sources(
    query: str, num: int = 10, client_ip: str = "unknown"
) -> tuple[list[dict[str, str | None]], bool, str | None]:
    """Return (results, cached, retrieved_at_iso). Raises SearchNotConfigured,
    SearchQuotaExhausted, or SearchFailed. Deduplication: identical
    concurrent queries serialize on a per-query lock and the second
    caller hits the cache instead of the provider."""
    settings = get_settings()
    normalized = normalize_query(query)
    provider = get_provider()
    limit = min(max(1, num), settings.discovery_results_limit)
    with _lock_for(normalized):
        cached = get_cached(normalized, settings.discovery_cache_ttl_seconds)
        if cached is not None:
            results, retrieved_at = cached
            return results[:limit], True, retrieved_at
        # Quota is checked inside the lock so concurrent identical
        # requests cannot both slip past a nearly-full quota.
        try:
            check_and_record(client_ip, settings.discovery_daily_global_limit, settings.discovery_session_limit)
        except QuotaExceeded as exc:
            raise SearchQuotaExhausted(str(exc)) from exc
        try:
            results = provider.search(query, limit)
        except ProviderQuotaExhausted as exc:
            raise SearchQuotaExhausted(str(exc)) from exc
        except ProviderError as exc:
            raise SearchFailed(str(exc)) from exc
        retrieved_at = datetime.now(timezone.utc).isoformat()
        set_cached(normalized, results)
        return results, False, retrieved_at
