"""Endpoint checks for POST /api/analyze.

Live URL fetching is mocked at the collector boundary so these
tests never touch the real internet. Pasted-text runs need no
mocking at all. The old endpoints are asserted unchanged, because
this layer must not redesign the frontend contract.
"""

import pytest
from fastapi.testclient import TestClient

import app.collector as collector_mod
from app.fetcher import FetchedPage
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _no_groq(monkeypatch):
    monkeypatch.setattr("app.analyzer.derive_questions_with_groq", lambda goal: None)


def test_analyze_pasted_texts_returns_strict_shape():
    text = (
        "Students are eligible when family income is below the limit. "
        "The last date to apply is 31 December 2026. "
        "Apply online through the national portal."
    )
    body = client.post("/api/analyze", json={
        "goal": "Scholarship application",
        "questions": ["Who is eligible?", "When is the last date to apply?", "What renews the scholarship next year?"],
        "texts": [{"title": "Pasted guide", "text": text}],
    }).json()
    assert body["mode"] == "live"
    assert body["questions_analyzed"] == 3
    assert body["coverage_percent"] == 67  # 2 covered of 3.
    by_id = {c["question_id"]: c for c in body["coverage"]}
    assert by_id["Q1"]["status"] == "covered"
    assert by_id["Q2"]["status"] == "covered"
    assert by_id["Q3"]["status"] == "not_found"
    assert "What renews the scholarship next year?" in body["unanswered_questions"]
    # Every quote must be a substring of the pasted text.
    for item in body["coverage"]:
        for evidence in item["evidence"]:
            assert evidence["quote"] in text
    assert body["analysis_method"] == "deterministic"
    assert body["sources"][0]["kind"] == "pasted_text"
    assert body["sources"][0]["date_status"] == "unknown"
    assert body["sources"][0]["published_date"] is None


def test_analyze_sample_mode_needs_no_inputs_and_is_labelled():
    body = client.post("/api/analyze", json={"mode": "offline_sample"}).json()
    assert body["mode"] == "offline_sample"
    assert "Demo data only" in body["disclaimer"]
    assert body["coverage_percent"] == 86
    assert all(s["is_sample"] is True for s in body["sources"])
    assert all(s["url"] is None for s in body["sources"])
    assert any(g["kind"] == "unanswered" for g in body["gaps"])
    assert len(body["conflicts"]) == 1


def test_analyze_rejects_missing_goal_inputs_and_unknown_fields():
    assert client.post("/api/analyze", json={"goal": "ab", "texts": [{"text": "Some text here."}]}).status_code == 422
    assert client.post("/api/analyze", json={"goal": "Scholarship application"}).status_code == 422
    assert client.post("/api/analyze", json={
        "goal": "Scholarship application",
        "texts": [{"text": "Some text here."}],
        "surprise_field": True,
    }).status_code == 422
    assert client.post("/api/analyze", json={
        "goal": "Scholarship application",
        "texts": [{"text": "x"}] * 21,
    }).status_code == 422


def test_analyze_url_success_and_failure_are_both_marked(monkeypatch):
    def _fake_fetch(url):
        if "good" in url:
            return FetchedPage(
                url=url, status="ok", title="Good page",
                text="Students are eligible when family income is below the limit.",
                content_type="text/html",
            )
        return FetchedPage(url=url, status="not_found", error="The page does not exist (HTTP 404).")
    monkeypatch.setattr(collector_mod, "fetch_url_record", _fake_fetch)
    body = client.post("/api/analyze", json={
        "goal": "Scholarship application",
        "questions": ["Who is eligible?"],
        "urls": ["https://example.com/good", "https://example.com/gone"],
    }).json()
    by_id = {s["id"]: s for s in body["sources"]}
    assert by_id["S1"]["fetch_status"] == "ok"
    assert by_id["S2"]["fetch_status"] == "not_found"
    assert body["inaccessible_source_ids"] == ["S2"]
    assert body["coverage"][0]["status"] == "covered"
    assert any("S2" in a["source_ids"] for a in body["actions"])


def test_parallel_fetch_keeps_input_order(monkeypatch):
    """Two 0.4 s fetches must finish in ~0.4 s, not ~0.8 s, and
    source IDs must still follow input order (executor.map)."""
    import time

    def _slow_fetch(url):
        time.sleep(0.4)
        return FetchedPage(url=url, status="ok", title="Slow page",
                           text="Students are eligible when family income is below the limit.",
                           content_type="text/html")
    monkeypatch.setattr(collector_mod, "fetch_url_record", _slow_fetch)
    started = time.time()
    body = client.post("/api/analyze", json={
        "goal": "Scholarship application",
        "questions": ["Who is eligible?"],
        "urls": ["https://example.com/first", "https://example.com/second"],
    }).json()
    assert time.time() - started < 0.7
    assert [s["id"] for s in body["sources"]] == ["S1", "S2"]
    assert body["sources"][0]["url"] == "https://example.com/first"
    assert body["sources"][1]["url"] == "https://example.com/second"


def test_old_endpoints_unchanged():
    health = client.get("/api/health").json()
    assert health["status"] == "ok"
    sample = client.get("/api/sample").json()
    assert sample["mode"] == "offline_sample"
    assert sample["coverage_percent"] == 86
    fetched = client.post("/api/fetch", json={"url": "http://localhost:9999/secret"}).json()
    assert fetched["status"] == "blocked"
    assert fetched["text_excerpt"] is None
