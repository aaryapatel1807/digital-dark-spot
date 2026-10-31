"""Fetch one user-supplied public URL (Requests + BeautifulSoup).

Scope, stated plainly:
- Only the URL the user pastes. No search, no crawling, no bulk
  scraping, no login, no paywall bypass.
- Blocked / paywalled / failed pages become a result with a clear
  message, never a crash and never invented text.
- The hostname guard below is a basic safety check, not a full SSRF
  proof; it is documented as a limitation in the README.

This foundation step fetches and extracts text only. It does not
analyse, summarise, or cite the page — that is a later layer.
"""

from __future__ import annotations

import ipaddress
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .config import get_settings
from .schemas import FetchResponse

_USER_AGENT = "GapLens/0.1 (foundation; user-supplied URL fetch)"
_BLOCKED_HOST_SUFFIXES = (".local", ".internal", ".lan")
_BLOCKED_HOSTS = {"localhost", "metadata.google.internal"}


def _hostname_is_blocked(hostname: str) -> bool:
    host = hostname.lower().strip(".")
    if host in _BLOCKED_HOSTS or host.endswith(_BLOCKED_HOST_SUFFIXES):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False  # A DNS name, not a literal IP; nothing more to check here.
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved


def fetch_public_url(raw_url: str) -> FetchResponse:
    now = datetime.now(timezone.utc)
    parsed = urlparse(raw_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return FetchResponse(url=raw_url, status="failed", error="Only http(s) URLs can be fetched.", fetched_at=now)
    if _hostname_is_blocked(parsed.hostname):
        return FetchResponse(url=raw_url, status="blocked", error="Local or private addresses are not fetched.", fetched_at=now)

    settings = get_settings()
    try:
        response = requests.get(
            raw_url,
            headers={"User-Agent": _USER_AGENT},
            timeout=settings.fetch_timeout_seconds,
            stream=True,
        )
    except requests.RequestException:
        return FetchResponse(url=raw_url, status="failed", error="The page could not be reached (network error or timeout).", fetched_at=now)

    content_type = response.headers.get("Content-Type", "")
    if response.status_code in (401, 403, 429):
        return FetchResponse(
            url=raw_url, status="blocked", content_type=content_type,
            error=f"The site refused this request (HTTP {response.status_code}). It may be paywalled or bot-protected.",
            fetched_at=now,
        )
    if response.status_code >= 400:
        return FetchResponse(
            url=raw_url, status="failed", content_type=content_type,
            error=f"The site returned HTTP {response.status_code}.",
            fetched_at=now,
        )
    if "html" not in content_type and "text" not in content_type:
        return FetchResponse(
            url=raw_url, status="unsupported", content_type=content_type,
            error="Only HTML/text pages are extracted in this foundation build.",
            fetched_at=now,
        )

    body = b""
    for chunk in response.iter_content(chunk_size=8192):
        body += chunk
        if len(body) >= settings.fetch_max_bytes:
            break
    soup = BeautifulSoup(body, "html.parser")
    for tag in soup(["script", "style", "nav", "noscript"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()
    return FetchResponse(
        url=raw_url, status="ok", title=title,
        text_excerpt=text[:1000] if text else None,
        content_type=content_type, fetched_at=now,
    )
