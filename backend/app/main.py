"""GapLens API — analysis layer.

Endpoints:
  GET  /            service info (no secrets)
  GET  /api/health health + whether Groq is configured (boolean only)
  GET  /api/sample honest offline sample analysis, labelled as a sample
  POST /api/fetch  fetch one user-supplied public URL, extract text
  POST /api/analyze full source processing + AI-assisted analysis:
         research goal + public URLs + pasted text in, strict
         Pydantic result out (summary, coverage, unanswered
         questions, possible conflicts, freshness warnings,
         prioritized actions). mode=offline_sample returns the
         bundled demo through the same engine, clearly labelled.

The frontend is untouched by this layer: it keeps calling health,
sample, and fetch exactly as before, and can adopt /api/analyze
later without any backend change.
Run with:  uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .analysis_schemas import AnalysisResponse, AnalyzeRequest
from .analyzer import analyze
from .collector import collect_sources
from .config import get_settings
from .fetcher import fetch_public_url
from .sample import build_sample_analysis
from .sample_analysis import build_sample_analysis_response
from .schemas import FetchRequest, FetchResponse, HealthResponse, SampleAnalysis

settings = get_settings()

app = FastAPI(title="GapLens", version=settings.version, description="AI-assisted information gap detection — analysis API.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_LIVE_DISCLAIMER = (
    "Live analysis over the sources you supplied. Findings are "
    "potential signals drawn from quoted passages, not confirmed "
    "facts. Verify the quotes against the original pages before "
    "acting on them."
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


@app.post("/api/analyze", response_model=AnalysisResponse)
def analyze_endpoint(payload: AnalyzeRequest) -> AnalysisResponse:
    if payload.mode == "offline_sample":
        # The bundled demo has its own fixed topic; a request goal
        # is ignored here so the sample can never look like a live
        # result about something else.
        return build_sample_analysis_response()
    assert payload.goal is not None  # Guaranteed by the request validator.
    collected = collect_sources(payload.urls, payload.texts)
    return analyze(payload.goal, payload.questions, collected, "live", _LIVE_DISCLAIMER)
