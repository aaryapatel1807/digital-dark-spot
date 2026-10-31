"""Regression tests for the 31 Oct 2026 QA/security audit findings.

Each test names the audit failure it pins:
- A1: transport errors (SSL/proxy/connection) crashed with 500 because
  the fetcher referenced requests.SSLError, which does not exist as
  a top-level attribute. They must now return a failed fetch result.
- A2: "Rs. 10000" vs "Rs. 12000" produced no conflict (money regex
  only knew ₹/$/€/£). Rs./INR must now be detected as money.
- A3: no security headers on API responses.
- A4: no rate limiting on /api/fetch and /api/analyze.
- A5: whitespace-only pasted text slipped through as an ok source
  with no text, counted as neither accessible nor inaccessible.
- A6: Groq returning invalid JSON / 429 / timeout must fall back to
  template questions (derive returns None), never crash.
- A7: a redirect to a numeric-IP private target must be blocked.
"""

import socket

import pytest
import requests
from fastapi.testclient import TestClient
from requests.exceptions import ConnectionError as ReqConnectionError
from requests.exceptions import ProxyError, SSLError

from app.config import get_settings
from app.fetcher import fetch_url_record
from app.groq_client import derive_questions_with_groq
from app.main import app
from app.ratelimit import reset_rate_limits

client = TestClient(app)


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


@pytest.mark.parametrize("exc", [SSLError("bad cert"), ReqConnectionError("conn reset"), ProxyError("proxy down")])
def test_transport_errors_are_failed_not_crash(monkeypatch, exc):
    _public_dns(monkeypatch)
    monkeypatch.setattr(requests, "get", lambda *a, **k: (_ for _ in ()).throw(exc))
    page = fetch_url_record("https://example.com/page")
    assert page.status == "failed"
    assert page.text is None


def test_rs_money_conflict_is_flagged():
    reset_rate_limits()
    payload = {
        "goal": "Scholarship application",
        "questions": ["What is the scholarship fee?"],
        "texts": [
            {"title": "Official", "text": "The scholarship fee is Rs. 10000 per year for all students."},
            {"title": "Blog", "text": "The scholarship fee is Rs. 12000 per year for all students."},
        ],
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["conflicts"], "Rs. fee disagreement must be a possible conflict"
    assert body["conflicts"][0]["label"] == "possible conflict"


def test_security_headers_on_api_response():
    response = client.get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_whitespace_pasted_text_is_rejected():
    reset_rate_limits()
    response = client.post("/api/analyze", json={"goal": "Test topic", "texts": [{"text": "   "}]})
    assert response.status_code == 422


@pytest.mark.parametrize("kind", ["bad_json", "wrong_shape", "http_429", "timeout"])
def test_groq_failures_fall_back(monkeypatch, kind):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    get_settings.cache_clear()
    try:
        import app.groq_client as groq_module

        class FakeGroqResponse:
            status_code = 429 if kind == "http_429" else 200

            def json(self):
                if kind == "bad_json":
                    raise ValueError("not json")
                if kind == "wrong_shape":
                    return {"questions": "not a list"}
                return {"choices": [{"message": {"content": '{"questions": []}'}}]}

        def _post(*args, **kwargs):
            if kind == "timeout":
                raise requests.Timeout()
            return FakeGroqResponse()

        monkeypatch.setattr(groq_module.requests, "post", _post)
        assert derive_questions_with_groq("Scholarship application") is None
    finally:
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        get_settings.cache_clear()


def test_redirect_to_numeric_private_is_blocked(monkeypatch):
    # A blanket "public DNS" mock would lie about the numeric host too
    # (it would resolve 2130706433 to a public IP), so resolve it the
    # way a real resolver does: the decimal form of 127.0.0.1.
    def _dns(host, port):
        ip = "127.0.0.1" if host == "2130706433" else "93.184.216.34"
        return [(socket.AF_INET, None, None, None, (ip, 0))]

    monkeypatch.setattr(socket, "getaddrinfo", _dns)
    calls: list[str] = []

    def _get(url, **kwargs):
        calls.append(url)
        return FakeResponse(status=302, headers={"Location": "http://2130706433/secret"})

    monkeypatch.setattr(requests, "get", _get)
    page = fetch_url_record("https://example.com/start")
    assert page.status == "blocked"
    assert calls == ["https://example.com/start"]


def test_rate_limit_analyze_returns_429():
    reset_rate_limits()
    payload = {"goal": "Test topic", "texts": [{"text": "Some text about a topic worth reading here."}]}
    codes = [client.post("/api/analyze", json=payload).status_code for _ in range(31)]
    assert codes[:30] == [200] * 30
    assert codes[30] == 429
    reset_rate_limits()
