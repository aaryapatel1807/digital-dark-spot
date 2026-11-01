"""Source discovery tests: no key = honest 503, bad provider = 502,
results come only from the provider response, never invented."""

from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.search import SearchFailed, SearchNotConfigured

client = TestClient(app)


def test_discover_without_key_is_503(monkeypatch):
    monkeypatch.setattr("app.main.discover_sources", lambda q, n: (_ for _ in ()).throw(SearchNotConfigured("not configured")))
    response = client.post("/api/discover", json={"query": "scholarship eligibility"})
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_discover_provider_failure_is_502(monkeypatch):
    monkeypatch.setattr("app.main.discover_sources", lambda q, n: (_ for _ in ()).throw(SearchFailed("provider down")))
    response = client.post("/api/discover", json={"query": "scholarship eligibility"})
    assert response.status_code == 502


def test_discover_returns_provider_results_only(monkeypatch):
    def fake(query, num):
        return [
            {"title": "Official page", "link": "https://example.com/scholarship", "snippet": "Eligibility details."},
            {"title": "Blog", "link": "https://example.com/blog", "snippet": None},
        ]
    monkeypatch.setattr("app.main.discover_sources", fake)
    response = client.post("/api/discover", json={"query": "scholarship eligibility"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 2
    assert body["results"][0]["link"] == "https://example.com/scholarship"
    assert body["results"][1]["snippet"] is None


def test_search_filters_non_http_links(monkeypatch):
    import app.search as search_module

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"organic_results": [
                {"title": "Good", "link": "https://example.com/good", "snippet": "x"},
                {"title": "Bad", "link": "ftp://example.com/bad", "snippet": "y"},
                {"title": "No link", "snippet": "z"},
            ]}

    monkeypatch.setattr(search_module, "get_settings", lambda: type("S", (), {"search_api_key": "test-key"})())
    monkeypatch.setattr(search_module.requests, "get", lambda *a, **k: FakeResponse())
    results = search_module.discover_sources("scholarship")
    assert [r["link"] for r in results] == ["https://example.com/good"]
