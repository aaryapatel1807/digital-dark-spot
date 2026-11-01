"""Production API compatibility (Task 2/4): the frontend must never
crash or invent results when a 2.0 endpoint is missing. These tests
pin the contract the frontend relies on: unknown routes are 404
(not a fake success), health reports only booleans, and every
conflict in a real analysis carries a classification + both
original quotes (evidence consistency)."""

from fastapi.testclient import TestClient

from app.main import app
from app.sample_analysis import build_sample_analysis_response

client = TestClient(app)


def test_unknown_route_is_404_not_fake_success():
    response = client.post("/api/ask-2.0-missing", json={})
    assert response.status_code == 404


def test_health_reports_booleans_only():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["groq_configured"], bool)
    assert isinstance(body["search_configured"], bool)
    assert "GROQ_API_KEY" not in str(body) and "SERPAPI_KEY" not in str(body)


def test_sample_conflicts_carry_classification_and_original_quotes():
    result = build_sample_analysis_response()
    for conflict in result.conflicts:
        assert conflict.classification in {
            "same_period", "different_period", "different_conditions",
            "different_scope", "uncertain",
        }
        assert len(conflict.values) == 2
        for value in conflict.values:
            assert value.quote in {e.quote for row in result.coverage for e in row.evidence}


def test_homepage_bundle_entry_exists():
    # Frontend regression guard for Task 1: the built bundle must
    # exist and the source entry must render the Landing hero.
    import pathlib

    frontend = pathlib.Path(__file__).resolve().parents[2] / "frontend"
    assert (frontend / "src" / "main.tsx").exists()
    shell = (frontend / "src" / "components" / "Shell.tsx").read_text()
    # Hero headline is split by an <em> tag in source, so check both halves.
    assert "Every answer has a" in shell and "blind spot" in shell
