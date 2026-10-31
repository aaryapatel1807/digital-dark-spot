"""Foundation checks for the GapLens API (run: python -m pytest tests/ -q).

These assert the honesty guarantees, not just 200s:
- health never leaks a key, only a boolean;
- the sample is labelled offline_sample with sample-only sources;
- the fetch guard refuses private addresses instead of fetching them.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_shape_and_no_secret_leak() -> None:
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["service"] == "GapLens"
    assert isinstance(body["groq_configured"], bool)
    assert "GROQ" not in str(body) and "groq_api_key" not in body


def test_sample_is_labelled_offline_demo() -> None:
    body = client.get("/api/sample").json()
    assert body["mode"] == "offline_sample"
    assert "Demo data only" in body["disclaimer"]
    assert body["coverage_percent"] == 86
    assert all(source["is_sample"] is True for source in body["sources"])
    assert all(source["url"] is None for source in body["sources"])
    assert any(slot["status"] == "gap" for slot in body["slots"])
    assert body["conflicts"] and body["conflicts"][0]["label"] == "possible conflict"


def test_fetch_guard_blocks_private_hosts() -> None:
    body = client.post("/api/fetch", json={"url": "http://localhost:9999/secret"}).json()
    assert body["status"] == "blocked"
    assert body["text_excerpt"] is None


def test_fetch_rejects_non_http() -> None:
    response = client.post("/api/fetch", json={"url": "ftp://example.com/file"})
    assert response.status_code == 422  # Pydantic HttpUrl rejects it.
