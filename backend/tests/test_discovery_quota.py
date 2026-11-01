"""Discovery quota/cache tests (Part 4): cache hits consume no
quota, quota exhaustion is friendly and does not call the provider,
provider quota errors are not retried, and manual analysis never
needs a provider (covered by existing analyze tests)."""

import app.search as search_module
from app.search import SearchQuotaExhausted, discover_sources


class FakeSettings:
    search_api_key = "test-key"
    search_provider = "serpapi"
    discovery_enabled = True
    discovery_daily_global_limit = 30
    discovery_session_limit = 3
    discovery_results_limit = 5
    discovery_cache_ttl_seconds = 86400


def _setup(monkeypatch, tmp_path, calls):
    monkeypatch.setenv("DISCOVERY_QUOTA_PATH", str(tmp_path / "quota.json"))
    monkeypatch.setattr(search_module, "get_settings", lambda: FakeSettings())

    class FakeProvider:
        name = "fake"

        def search(self, query, limit):
            calls.append(query)
            return [{"title": "Official", "link": "https://example.com/x", "snippet": "s"}]

    monkeypatch.setattr(search_module, "get_provider", lambda: FakeProvider())


def test_cache_hit_consumes_no_quota_and_no_provider_call(monkeypatch, tmp_path):
    calls: list = []
    _setup(monkeypatch, tmp_path, calls)
    first, cached1, _ = discover_sources("scholarship eligibility", 5, "1.2.3.4")
    second, cached2, retrieved = discover_sources("Scholarship  Eligibility", 5, "1.2.3.4")
    assert cached1 is False and cached2 is True
    assert retrieved is not None
    assert len(calls) == 1
    assert first == second


def test_session_quota_exhaustion_blocks_provider(monkeypatch, tmp_path):
    calls: list = []
    _setup(monkeypatch, tmp_path, calls)
    for i in range(3):
        discover_sources(f"different query {i}", 5, "9.9.9.9")
    try:
        discover_sources("one more query", 5, "9.9.9.9")
    except SearchQuotaExhausted as exc:
        assert "limit reached" in str(exc)
    else:
        raise AssertionError("session quota was not enforced")
    assert len(calls) == 3


def test_provider_quota_error_is_not_retried(monkeypatch, tmp_path):
    from app.search_providers import ProviderQuotaExhausted

    calls: list = []
    monkeypatch.setenv("DISCOVERY_QUOTA_PATH", str(tmp_path / "quota.json"))
    monkeypatch.setattr(search_module, "get_settings", lambda: FakeSettings())

    class QuotaProvider:
        name = "fake"

        def search(self, query, limit):
            calls.append(query)
            raise ProviderQuotaExhausted("quota exhausted")

    monkeypatch.setattr(search_module, "get_provider", lambda: QuotaProvider())
    try:
        discover_sources("scholarship", 5, "1.1.1.1")
    except SearchQuotaExhausted:
        pass
    else:
        raise AssertionError("provider quota error was not surfaced")
    assert len(calls) == 1


def test_cache_expiration_refetches(monkeypatch, tmp_path):
    calls: list = []
    monkeypatch.setenv("DISCOVERY_QUOTA_PATH", str(tmp_path / "quota.json"))
    settings = FakeSettings()
    settings.discovery_cache_ttl_seconds = 0
    monkeypatch.setattr(search_module, "get_settings", lambda: settings)

    class FakeProvider:
        name = "fake"

        def search(self, query, limit):
            calls.append(query)
            return [{"title": "Official", "link": "https://example.com/x", "snippet": "s"}]

    monkeypatch.setattr(search_module, "get_provider", lambda: FakeProvider())
    discover_sources("scholarship", 5, "2.2.2.2")
    discover_sources("scholarship", 5, "2.2.2.2")
    # TTL 0 means the entry is immediately stale, so both calls hit the provider.
    assert len(calls) == 2
