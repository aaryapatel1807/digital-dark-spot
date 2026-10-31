"""SSRF-safe fetch of user-supplied public URLs (Requests + BeautifulSoup).

This replaces the foundation fetcher's basic hostname guard with a
defense that is checked at every step, because a fetch that trusts
the first hostname is not safe:

- Scheme must be http(s); URLs carrying credentials are refused.
- Literal IPs and DNS-resolved IPs are rejected when they can reach
  internal services: RFC1918 private, loopback, link-local (incl.
  cloud metadata 169.254.169.254), CGNAT, unique-local IPv6,
  unspecified, or multicast. Benchmarking/documentation ranges are
  NOT blocked: ipaddress.is_private covers them, and egress proxies
  legitimately return them for public hostnames.
- Redirects are followed manually (max 3) and every hop is
  re-validated the same way, including fresh DNS resolution.
- Per-request timeout, per-page byte cap, HTML/text only.

What this does NOT prove (documented honestly): DNS can change
between validation and connection (TOCTOU / rebinding). The check
happens immediately before each request, which closes the casual
hole; a determined rebinding attack against a shared resolver is
outside this layer's threat model. Pages that need JavaScript to
render are not executed — only served HTML/text is extracted.

Error taxonomy, kept distinct on purpose:
- "not_found": the host exists but the page does not (HTTP 404/410).
- "nonexistent": the host does not resolve (DNS failure).
- "blocked": the URL was refused for safety, or the site refused us
  (401/403/429 — paywall or bot protection).
- "timeout": the site did not answer in time.
- "too_large": the page exceeds the byte cap.
- "failed": anything else (other HTTP errors, TLS errors, ...).
- "unsupported": a non-HTML/text response.
"""

from __future__ import annotations

import ipaddress
import json
import re
import socket
from dataclasses import dataclass
from datetime import date, datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.exceptions import SSLError

from .config import get_settings
from .schemas import FetchResponse, FetchStatus

_USER_AGENT = "GapLens/0.2 (user-supplied URL fetch)"
_BLOCKED_HOST_SUFFIXES = (".local", ".internal", ".lan", ".localhost")
_BLOCKED_HOSTS = {"localhost", "metadata.google.internal"}
_DATE_META_KEYS = (
    ("property", "article:published_time"),
    ("property", "article:modified_time"),
    ("name", "date"),
    ("name", "publish_date"),
    ("name", "DC.date"),
    ("name", "DC.Date"),
    ("itemprop", "datePublished"),
)
_DATE_FORMATS = ("%Y-%m-%d", "%d %b %Y", "%B %d, %Y", "%d %B %Y", "%Y/%m/%d")


@dataclass
class FetchedPage:
    """One fetch attempt, successful or not. Never invents text."""

    url: str  # Final URL after redirects (or the requested one).
    status: FetchStatus
    title: str | None = None
    text: str | None = None
    published_date: date | None = None
    content_type: str | None = None
    error: str | None = None


def _ip_is_forbidden(ip: ipaddress._BaseAddress) -> bool:
    """True only for addresses that can reach internal services.

    Deliberately NOT ipaddress.is_private: that flag is too broad —
    it also covers benchmarking (198.18.0.0/15) and documentation
    ranges, which egress proxies legitimately return for public
    hostnames. Blocking those would break every fetch behind such a
    proxy while adding no safety: those ranges are unroutable and
    cannot host an internal service. What stays blocked:
    RFC1918 private, loopback, link-local (incl. cloud metadata
    169.254.169.254), CGNAT, unique-local IPv6, unspecified, and
    multicast.
    """
    if ip.is_multicast or ip.is_unspecified or ip.is_loopback or ip.is_link_local:
        return True
    if isinstance(ip, ipaddress.IPv4Address):
        return any(
            ip in network
            for network in (
                ipaddress.IPv4Network("10.0.0.0/8"),
                ipaddress.IPv4Network("172.16.0.0/12"),
                ipaddress.IPv4Network("192.168.0.0/16"),
                ipaddress.IPv4Network("100.64.0.0/10"),
            )
        )
    return ip in ipaddress.IPv6Network("fc00::/7")


def _validate_target(url: str) -> tuple[str | None, FetchStatus | None, str | None]:
    """Validate one URL before fetching it.

    Returns (hostname, None, None) when the target may be fetched, or
    (None, status, error) when it must be refused. DNS failures are
    reported as "nonexistent", safety refusals as "blocked".
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None, "failed", "Only http(s) URLs can be fetched."
    if parsed.username or parsed.password:
        return None, "blocked", "URLs carrying credentials are not fetched."
    host = parsed.hostname.lower().strip(".")
    if host in _BLOCKED_HOSTS or host.endswith(_BLOCKED_HOST_SUFFIXES):
        return None, "blocked", "Local or private addresses are not fetched."
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        if _ip_is_forbidden(ip):
            return None, "blocked", "Local or private addresses are not fetched."
        return host, None, None
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return None, "nonexistent", "The host does not resolve (DNS failure)."
    except OSError:
        return None, "failed", "The host could not be resolved."
    if not infos:
        return None, "nonexistent", "The host does not resolve (DNS failure)."
    for info in infos:
        try:
            resolved = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if _ip_is_forbidden(resolved):
            return None, "blocked", "Local or private addresses are not fetched."
    return host, None, None


def _parse_date(raw: str) -> date | None:
    text = raw.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        pass
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    return None


def _extract_date(soup: BeautifulSoup) -> date | None:
    for attr, key in _DATE_META_KEYS:
        tag = soup.find("meta", attrs={attr: key})
        content = (tag.get("content") or "").strip() if tag else ""
        parsed = _parse_date(content) if content else None
        if parsed:
            return parsed
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
        except (ValueError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            for key in ("datePublished", "dateCreated"):
                value = item.get(key)
                if isinstance(value, str):
                    parsed = _parse_date(value)
                    if parsed:
                        return parsed
    time_tag = soup.find("time", attrs={"datetime": True})
    if time_tag:
        parsed = _parse_date(str(time_tag.get("datetime")))
        if parsed:
            return parsed
    return None


def _extract_title(soup: BeautifulSoup) -> str | None:
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and (og.get("content") or "").strip():
        return str(og["content"]).strip()
    if soup.title and soup.title.string and soup.title.string.strip():
        return soup.title.string.strip()
    return None


def _extract_text(soup: BeautifulSoup) -> str:
    container = soup.find("article") or soup.find("main") or soup.body or soup
    for tag in container.find_all(["script", "style", "nav", "noscript", "template"]):
        tag.decompose()
    return re.sub(r"\s+", " ", container.get_text(" ")).strip()


def fetch_url_record(raw_url: str) -> FetchedPage:
    """Fetch one URL with SSRF checks, redirect re-validation, and limits."""
    settings = get_settings()
    current = raw_url
    redirects = 0
    while True:
        _, status, error = _validate_target(current)
        if status is not None:
            return FetchedPage(url=current, status=status, error=error)
        try:
            response = requests.get(
                current,
                headers={"User-Agent": _USER_AGENT},
                timeout=settings.fetch_timeout_seconds,
                allow_redirects=False,
                stream=True,
            )
        except requests.Timeout:
            return FetchedPage(url=current, status="timeout", error="The site did not answer in time.")
        except SSLError:
            # NB: requests.SSLError does NOT exist as a top-level attribute
            # in this requests version — the old code raised AttributeError
            # here and turned every SSL/proxy failure into a 500. The
            # exception class must come from requests.exceptions.
            return FetchedPage(url=current, status="failed", error="The site's TLS certificate could not be verified.")
        except requests.RequestException:
            return FetchedPage(url=current, status="failed", error="The page could not be reached (network error).")

        content_type = response.headers.get("Content-Type", "")
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("Location")
            if not location or redirects >= settings.max_redirects:
                return FetchedPage(
                    url=current, status="failed", content_type=content_type,
                    error="Too many redirects or a redirect without a destination.",
                )
            redirects += 1
            current = urljoin(current, location)
            continue
        if response.status_code in (401, 403, 429):
            return FetchedPage(
                url=current, status="blocked", content_type=content_type,
                error=f"The site refused this request (HTTP {response.status_code}). It may be paywalled or bot-protected.",
            )
        if response.status_code in (404, 410):
            return FetchedPage(
                url=current, status="not_found", content_type=content_type,
                error=f"The page does not exist (HTTP {response.status_code}).",
            )
        if response.status_code >= 400:
            return FetchedPage(
                url=current, status="failed", content_type=content_type,
                error=f"The site returned HTTP {response.status_code}.",
            )
        if "html" not in content_type and "text" not in content_type:
            return FetchedPage(
                url=current, status="unsupported", content_type=content_type,
                error="Only HTML/text pages are extracted.",
            )
        body = b""
        too_large = False
        for chunk in response.iter_content(chunk_size=8192):
            body += chunk
            if len(body) > settings.fetch_max_bytes:
                too_large = True
                break
        if too_large:
            return FetchedPage(
                url=current, status="too_large", content_type=content_type,
                error=f"The page exceeds the {settings.fetch_max_bytes:,} byte extraction limit.",
            )
        soup = BeautifulSoup(body, "html.parser")
        text = _extract_text(soup)
        return FetchedPage(
            url=current, status="ok", title=_extract_title(soup),
            text=text if text else None, published_date=_extract_date(soup),
            content_type=content_type,
        )


def fetch_public_url(raw_url: str) -> FetchResponse:
    """Single-URL endpoint adapter. Same shape as the foundation build."""
    now = datetime.now(timezone.utc)
    page = fetch_url_record(raw_url)
    return FetchResponse(
        url=page.url, status=page.status, title=page.title,
        text_excerpt=page.text[:1000] if page.text else None,
        content_type=page.content_type, error=page.error, fetched_at=now,
    )
