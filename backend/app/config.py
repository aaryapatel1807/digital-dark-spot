"""Backend-only configuration for GapLens.

Secrets live here, on the server, and are never sent to the frontend.
The frontend only ever learns *whether* a key is configured (a boolean
on the health endpoint), never the key itself. Nothing in this module
logs, prints, or returns a secret value.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()  # Reads backend/.env when present; .env is gitignored.


def _cors_origins() -> list[str]:
    # Both local frontend origins work out of the box: 5173 is the
    # Vite dev server, 4173 is `vite preview` of the production
    # build. Without 4173, the built app's health/analyze calls were
    # CORS-blocked in the browser (curl probes passed, so the failure
    # only showed up in a real browser — caught by the browser e2e).
    raw = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:4173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = "GapLens"
    version: str = "2.0.0"
    environment: str = field(default_factory=lambda: os.environ.get("ENVIRONMENT", "development"))
    cors_origins: list[str] = field(default_factory=_cors_origins)
    # Backend-only secret. Optional: the app runs fully in honest
    # offline sample mode when it is absent.
    groq_api_key: str | None = field(
        default_factory=lambda: os.environ.get("GROQ_API_KEY") or None
    )
    groq_model: str | None = field(
        default_factory=lambda: os.environ.get("GROQ_MODEL") or None
    )
    fetch_timeout_seconds: float = 10.0
    fetch_max_bytes: int = 1_000_000
    # Analysis-layer limits. These bound every /api/analyze run so one
    # request cannot fan out into a crawl or a multi-minute job.
    max_urls_per_request: int = 20
    max_texts_per_request: int = 20
    max_total_inputs_per_request: int = 20
    max_redirects: int = 3
    max_questions: int = 20
    pasted_text_max_chars: int = 200_000
    groq_timeout_seconds: float = 15.0
    # A source dated older than this is flagged stale. Undated sources
    # are never guessed: they are reported as unknown.
    freshness_stale_after_days: int = 365

    @property
    def groq_configured(self) -> bool:
        return bool(self.groq_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
