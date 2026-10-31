"""GapLens API — foundation build.

Endpoints in this foundation only:
  GET  /            service info (no secrets)
  GET  /api/health health + whether Groq is configured (boolean only)
  GET  /api/sample honest offline sample analysis, labelled as a sample
  POST /api/fetch  fetch one user-supplied public URL, extract text

No search endpoint, no generated citations, no analysis engine yet.
Run with:  uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .fetcher import fetch_public_url
from .sample import build_sample_analysis
from .schemas import FetchRequest, FetchResponse, HealthResponse, SampleAnalysis

settings = get_settings()

app = FastAPI(title="GapLens", version=settings.version, description="AI-assisted information gap detection — foundation API.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "GapLens", "version": settings.version, "docs": "/docs"}


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        version=settings.version,
        environment=settings.environment,
        groq_configured=settings.groq_configured,
        checked_at=datetime.now(timezone.utc),
    )


@app.get("/api/sample", response_model=SampleAnalysis)
def sample() -> SampleAnalysis:
    return build_sample_analysis()


@app.post("/api/fetch", response_model=FetchResponse)
def fetch(payload: FetchRequest) -> FetchResponse:
    return fetch_public_url(str(payload.url))
