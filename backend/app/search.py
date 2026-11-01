"""Source discovery via a configured search provider (GapLens 2.0, Step 3).

Rules, stated plainly:
- No provider key, no discovery: the endpoint returns 503 with a
  plain message, and the UI says search is not configured. URLs are
  NEVER invented — every result comes from the provider response.
- The key lives server-side only (SERPAPI_KEY env, like GROQ_API_KEY)
  and is never logged, returned, or sent to the frontend.
- Discovered results are SUGGESTIONS, not analyzed sources. A result
  becomes an analyzed source only when the user selects it and the
  existing SSRF-safe fetcher reads it in /api/analyze.
- Results are filtered to http(s) URLs only; anything else is dropped.
"""

from __future__ import annotations

import requests

from .config import get_settings

_ENDPOINT = "https://serpapi.com/search.json"
_TIMEOUT_SECONDS = 15.0


class SearchNotConfigured(Exception):
    pass


class SearchFailed(Exception):
    pass


def discover_sources(query: str, num: int = 10) -> list[dict[str, str | None]]:
    """Return provider results as {title, link, snippet} dicts."""
    settings = get_settings()
    if not settings.search_api_key:
        raise SearchNotConfigured(
            "Source discovery is not configured: set SERPAPI_KEY in the backend environment."
        )
    try:
        response = requests.get(
            _ENDPOINT,
            params={
                "engine": "google",
                "q": query,
                "num": max(1, min(num, 10)),
                "api_key": settings.search_api_key,
            },
            timeout=_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise SearchFailed(f"Search provider could not be reached: {type(exc).__name__}.") from exc
    if response.status_code != 200:
        raise SearchFailed(
            f"Search provider returned HTTP {response.status_code}. Check the provider key and quota."
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise SearchFailed("Search provider returned an unreadable response.") from exc
    results: list[dict[str, str | None]] = []
    for item in data.get("organic_results", []) or []:
        if not isinstance(item, dict):
            continue
        link = item.get("link")
        if not isinstance(link, str) or not link.startswith(("http://", "https://")):
            continue
        title = item.get("title")
        snippet = item.get("snippet")
        results.append(
            {
                "title": title if isinstance(title, str) else link,
                "link": link,
                "snippet": snippet if isinstance(snippet, str) else None,
            }
        )
    return results
