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
    raw = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = "GapLens"
    version: str = "0.1.0-foundation"
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

    @property
    def groq_configured(self) -> bool:
        return bool(self.groq_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
