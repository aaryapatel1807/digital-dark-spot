"""SSRF and fetch-mapping checks for the hardened fetcher.

The network is fully mocked here: DNS via socket.getaddrinfo and
HTTP via requests.get. No test below touches the real internet, and
no test trusts the VM's own resolver.
"""

import socket

import pytest
import requests

from app.config import get_settings
from app.fetcher import fetch_url_record


class FakeResponse:
    def __init__(self, status=200, headers=None, body=b""):
        self.status_code = status
        self.headers = headers or {"Content-Type": "text/html; charset=utf-8"}
        self._body = body

    def iter_content(self, chunk_size=8192):
        yield self._body


def _public_dns(monkeypatch):
    monkeypatch.setattr(
        socket, "getaddrinfo",
        lambda host, port: [(socket.AF_INET, None, None, None, ("93.184.216.34", 0))],
    )


def _fake_get(monkeypatch, response=None, exc=None, calls=None):
    def _get(*args, **kwargs):
        if calls is not None:
            calls.append(args[0])
        if exc is not None:
            raise exc
        return response
    monkeypatch.setattr(requests, "get", _get)


@pytest.mark.parametrize("url", [
    "http://localhost:9999/secret",
    "http://127.0.0.1/admin",
    "http://10.0.0.5/",
    "http://172.16.4.2/",
    "http://192.168.1.1/",
    "http://169.254.169.254/latest/meta-data/",
    "http://[::1]/",
    "http://metadata.google.internal/",
    "http://printer.local/",
    "http://user:pass@example.com/",
    "ftp://example.com/file",
])
def test_blocked_targets_never_reach_http(monkeypatch, url):
    _public_dns(monkeypatch)
    calls: list[str] = []
    _fake_get(monkeypatch, FakeResponse(), calls=calls)
    page = fetch_url_record(url)
    assert page.status in ("blocked", "failed")
    assert calls == []
    assert page.text is None


def test_dns_failure_is_nonexistent_not_not_found(monkeypatch):
    def _fail(host, port):
        raise socket.gaierror("Name or service not known")
    monkeypatch.setattr(socket, "getaddrinfo", _fail)
    calls: list[str] = []
    _fake_get(monkeypatch, FakeResponse(), calls=calls)
    page = fetch_url_record("https://this-host-does-not-exist-xyz.example/")
    assert page.status == "nonexistent"
    assert "does not resolve" in (page.error or "")
    assert calls == []


def test_private_dns_resolution_is_blocked(monkeypatch):
    monkeypatch.setattr(
        socket, "getaddrinfo",
        lambda host, port: [(socket.AF_INET, None, None, None, ("10.1.2.3", 0))],
    )
    calls: list[str] = []
    _fake_get(monkeypatch, FakeResponse(), calls=calls)
    page = fetch_url_record("https://internal.example.com/")
    assert page.status == "blocked"
    assert calls == []


@pytest.mark.parametrize("status", [404, 410])
def test_missing_page_is_not_found(monkeypatch, status):
    _public_dns(monkeypatch)
    _fake_get(monkeypatch, FakeResponse(status=status, body=b"nope"))
    page = fetch_url_record("https://example.com/gone")
    assert page.status == "not_found"
    assert page.text is None


def test_timeout_is_its_own_status(monkeypatch):
    _public_dns(monkeypatch)
    _fake_get(monkeypatch, exc=requests.Timeout())
    page = fetch_url_record("https://example.com/slow")
    assert page.status == "timeout"


def test_redirect_to_private_is_blocked(monkeypatch):
    _public_dns(monkeypatch)
    calls: list[str] = []
    redirect = FakeResponse(status=302, headers={"Location": "http://127.0.0.1/secret"})
    _fake_get(monkeypatch, redirect, calls=calls)
    page = fetch_url_record("https://example.com/redirect")
    assert page.status == "blocked"
    assert calls == ["https://example.com/redirect"]


def test_redirect_to_public_is_followed(monkeypatch):
    _public_dns(monkeypatch)
    calls: list[str] = []
    seen: list[str] = []

    def _get(url, **kwargs):
        seen.append(url)
        if "start" in url:
            return FakeResponse(status=302, headers={"Location": "https://example.com/page"})
        return FakeResponse(body=b"<html><head><title> Landed </title></head><body><p>Hello world, this is the page body.</p></body></html>")
    monkeypatch.setattr(requests, "get", _get)
    page = fetch_url_record("https://example.com/start")
    assert page.status == "ok"
    assert page.url == "https://example.com/page"
    assert page.title == "Landed"
    assert seen == ["https://example.com/start", "https://example.com/page"]


def test_benchmarking_range_from_egress_proxy_is_not_blocked(monkeypatch):
    """Regression: this VM's resolver returns 198.18.x.x (benchmarking)
    for public hostnames. That range cannot host an internal service,
    so it must pass the IP check; is_private would wrongly block it."""
    monkeypatch.setattr(
        socket, "getaddrinfo",
        lambda host, port: [(socket.AF_INET, None, None, None, ("198.18.152.134", 0))],
    )
    html = b"<html><head><title>Example Domain</title></head><body><p>This domain is for use in illustrative examples.</p></body></html>"
    _fake_get(monkeypatch, FakeResponse(body=html))
    page = fetch_url_record("https://example.com/")
    assert page.status == "ok"
    assert page.title == "Example Domain"


def test_extracts_title_meta_date_and_skips_chrome(monkeypatch):
    _public_dns(monkeypatch)
    html = (
        b"<html><head><title>Fallback title</title>"
        b'<meta property="og:title" content="Real page title">'
        b'<meta property="article:published_time" content="2026-03-15T10:00:00Z">'
        b"<style>.x{color:red}</style><script>var x = 1;</script></head>"
        b"<body><nav>Home About Contact</nav>"
        b"<article><p>The scholarship deadline is 31 December 2026 for all applicants.</p></article>"
        b"</body></html>"
    )
    _fake_get(monkeypatch, FakeResponse(body=html))
    page = fetch_url_record("https://example.com/article")
    assert page.status == "ok"
    assert page.title == "Real page title"
    assert page.published_date is not None and page.published_date.isoformat() == "2026-03-15"
    assert page.text is not None and "deadline is 31 December 2026" in page.text
    assert "Home About Contact" not in page.text
    assert "var x = 1" not in page.text


def test_json_ld_date_is_found(monkeypatch):
    _public_dns(monkeypatch)
    html = (
        b'<html><head><script type="application/ld+json">'
        b'{"@type": "Article", "datePublished": "2024-11-02"}'
        b"</script></head><body><p>Some article text worth reading here.</p></body></html>"
    )
    _fake_get(monkeypatch, FakeResponse(body=html))
    page = fetch_url_record("https://example.com/ld")
    assert page.published_date is not None and page.published_date.isoformat() == "2024-11-02"


def test_undated_page_reports_no_date(monkeypatch):
    _public_dns(monkeypatch)
    html = b"<html><body><p>An undated forum post about scholarships and deadlines.</p></body></html>"
    _fake_get(monkeypatch, FakeResponse(body=html))
    page = fetch_url_record("https://example.com/forum")
    assert page.status == "ok"
    assert page.published_date is None


def test_unsupported_content_type(monkeypatch):
    _public_dns(monkeypatch)
    _fake_get(monkeypatch, FakeResponse(headers={"Content-Type": "application/pdf"}))
    page = fetch_url_record("https://example.com/file.pdf")
    assert page.status == "unsupported"


def test_oversize_page_is_too_large(monkeypatch):
    _public_dns(monkeypatch)
    limit = get_settings().fetch_max_bytes
    _fake_get(monkeypatch, FakeResponse(body=b"x" * (limit + 1)))
    page = fetch_url_record("https://example.com/huge")
    assert page.status == "too_large"
    assert page.text is None
