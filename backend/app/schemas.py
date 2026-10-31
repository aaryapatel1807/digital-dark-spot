"""Typed API schemas for GapLens (Pydantic v2).

Every response the frontend renders is typed here first, so the
frontend's TypeScript types mirror these exactly. Findings are always
labelled "potential" / "possible" — never stated as confirmed facts.

The analysis layer lives in analysis_schemas.py (strict request and
response models for /api/analyze). This module keeps the foundation
shapes (health, offline sample, single-URL fetch) unchanged apart
from the fetch status taxonomy, which gained explicit values so an
inaccessible URL can say WHY it is inaccessible instead of just
failing: "not_found" is an HTTP 404/410 from a host that exists,
"nonexistent" is a host that does not resolve at all.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

SlotStatus = Literal["covered", "partial", "gap"]
# "failed" stays for generic failures. "not_found" (HTTP 404/410) and
# "nonexistent" (DNS failure) are deliberately different statuses:
# a missing page and a missing host are different facts.
FetchStatus = Literal[
    "ok", "blocked", "failed", "unsupported",
    "not_found", "nonexistent", "timeout", "too_large",
]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "GapLens"
    version: str
    environment: str
    # Boolean only. The key itself is never exposed.
    groq_configured: bool
    sample_mode_available: bool = True
    checked_at: datetime


class SampleSource(BaseModel):
    id: str
    label: str
    kind: Literal["official", "blog", "forum", "other"]
    # None on purpose: bundled demo sources have no real URL, and
    # inventing one would be a fake citation.
    url: str | None = None
    note: str
    is_sample: Literal[True] = True


class CoverageSlot(BaseModel):
    slot: str
    question: str
    status: SlotStatus
    source_ids: list[str] = Field(default_factory=list)


class SampleGap(BaseModel):
    slot: str
    title: str
    detail: str
    severity: Literal["high", "medium", "low"]


class ConflictValue(BaseModel):
    source_id: str
    value: str
    quote: str


class SampleConflict(BaseModel):
    slot: str
    label: Literal["possible conflict"] = "possible conflict"
    detail: str
    values: list[ConflictValue]


class SampleChecklistItem(BaseModel):
    rank: int
    action: str
    reason: str
    priority: Literal["high", "medium", "low"]


class SampleAnalysis(BaseModel):
    mode: Literal["offline_sample"] = "offline_sample"
    topic: str
    disclaimer: str = (
        "Demo data only. This analysis was NOT fetched from the web and "
        "describes no real scholarship. It shows the shape of a GapLens "
        "result so the interface can be reviewed without an API key."
    )
    coverage_percent: int
    sources: list[SampleSource]
    slots: list[CoverageSlot]
    gaps: list[SampleGap]
    conflicts: list[SampleConflict]
    checklist: list[SampleChecklistItem]


class FetchRequest(BaseModel):
    url: HttpUrl


class FetchResponse(BaseModel):
    url: str
    status: FetchStatus
    title: str | None = None
    text_excerpt: str | None = None
    content_type: str | None = None
    error: str | None = None
    fetched_at: datetime
    note: str = (
        "Fetched live from the URL you supplied. No analysis, gap, or "
        "citation is derived from it in this foundation build."
    )
