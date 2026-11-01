"""Provider-independent discovery architecture (Part 3).

A provider is any class with search(query, limit) -> list of
{title, link, snippet} dicts, filtered to http(s) links only.
Only SerpApi is implemented today; the interface exists so a
future provider (another legitimate API, a self-hosted service,
or an official public data source) can be added without touching
the endpoint, quota, or cache code. No provider is added merely
because it claims to be free, and no search engine is scraped:
results must come from a provider API the user has configured
and is permitted to use.
"""

from __future__ import annotations

import requests


class ProviderError(Exception):
    pass


class ProviderQuotaExhausted(ProviderError):
    pass


class SearchProvider:
    name: str = "base"

    def search(self, query: str, limit: int) -> list[dict[str, str | None]]:
        raise NotImplementedError


def _clean_results(items) -> list[dict[str, str | None]]:
    results: list[dict[str, str | None]] = []
    for item in items or []:
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


class SerpApiProvider(SearchProvider):
    name = "serpapi"
    _ENDPOINT = "https://serpapi.com/search.json"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, limit: int) -> list[dict[str, str | None]]:
        try:
            response = requests.get(
                self._ENDPOINT,
                params={"engine": "google", "q": query, "num": max(1, min(limit, 10)), "api_key": self.api_key},
                timeout=15.0,
            )
        except requests.RequestException as exc:
            raise ProviderError(f"Search provider could not be reached: {type(exc).__name__}.") from exc
        if response.status_code in (429, 403):
            body = ""
            try:
                body = str(response.json())
            except ValueError:
                body = response.text
            if response.status_code == 429 or any(
                word in body.lower() for word in ("quota", "billing", "exceeded", "insufficient", "credits")
            ):
                raise ProviderQuotaExhausted(
                    "Search provider quota exhausted. No further discovery searches will be attempted today; add website links or documents instead."
                )
            raise ProviderError(f"Search provider returned HTTP {response.status_code}. Check the provider key and quota.")
        if response.status_code != 200:
            raise ProviderError(f"Search provider returned HTTP {response.status_code}. Check the provider key and quota.")
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError("Search provider returned an unreadable response.") from exc
        return _clean_results(data.get("organic_results"))
