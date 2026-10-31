"""Strict Pydantic v2 schemas for POST /api/analyze.

Design rules for this layer:
- Requests forbid unknown fields, so a typo cannot silently change
  what is analysed. Limits are enforced by the schema itself, not
  by hoping the caller is polite.
- Every finding carries the evidence it rests on: source IDs and
  quoted passages. Quotes are validated server-side against the
  collected text before the response leaves (see analyzer.py) — a
  quote that is not a substring of its source never ships.
- "not_found" and "nonexistent" are different facts and stay
  different statuses, in fetch results and in coverage alike.
- An undated source is reported as date_status "unknown" with
  published_date null. Its freshness is never guessed.
- Findings are labelled "possible" / "potential" throughout. The
  engine reports what the sources say and what they do not say;
  it never states a conclusion the sources do not support.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from .schemas import FetchStatus

CoverageStatus = Literal["covered", "partial", "not_found"]
GapKind = Literal["unanswered", "partial", "single_source", "stale_only", "undated_only"]
FreshnessKind = Literal["stale", "undated"]
Priority = Literal["high", "medium", "low"]
QuestionOrigin = Literal["user", "derived"]
SourceKind = Literal["url", "pasted_text"]
AnalysisMode = Literal["live", "offline_sample"]


class PastedText(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=200)
    text: str = Field(min_length=1, max_length=200_000)


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Optional only because offline_sample mode needs no goal: the
    # bundled demo has its own fixed topic. Live mode requires one.
    goal: str | None = Field(default=None, max_length=2000)
    questions: list[str] | None = Field(default=None, max_length=20)
    urls: list[HttpUrl] = Field(default_factory=list, max_length=20)
    texts: list[PastedText] = Field(default_factory=list, max_length=20)
    mode: AnalysisMode = "live"

    @model_validator(mode="after")
    def _check_inputs(self) -> "AnalyzeRequest":
        if self.mode == "live":
            if self.goal is None or len(self.goal.strip()) < 3:
                raise ValueError("Live analysis needs a research goal of at least 3 characters.")
            self.goal = self.goal.strip()
            if not self.urls and not self.texts:
                raise ValueError(
                    "Live analysis needs at least one URL or pasted text. "
                    "Use mode=offline_sample for the bundled demo instead."
                )
            if len(self.urls) + len(self.texts) > 20:
                raise ValueError("At most 20 inputs (URLs + pasted texts) per analysis.")
        if self.questions is not None:
            cleaned = [q.strip() for q in self.questions if q.strip()]
            if not cleaned:
                raise ValueError("questions must not be empty when provided.")
            for q in cleaned:
                if len(q) > 500:
                    raise ValueError("Each question must be at most 500 characters.")
            self.questions = cleaned
        return self


class SourceRecord(BaseModel):
    id: str
    kind: SourceKind
    url: str | None = None
    title: str | None = None
    fetch_status: FetchStatus
    date_status: Literal["known", "unknown"]
    published_date: date | None = None
    text_excerpt: str | None = None
    text_length: int = 0
    error: str | None = None
    is_sample: bool = False


class EvidenceQuote(BaseModel):
    source_id: str
    quote: str = Field(max_length=500)


class QuestionCoverage(BaseModel):
    question_id: str
    question: str
    origin: QuestionOrigin
    status: CoverageStatus
    supporting_source_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceQuote] = Field(default_factory=list)


class PossibleConflict(BaseModel):
    question_id: str
    question: str
    label: Literal["possible conflict"] = "possible conflict"
    detail: str
    values: list[EvidenceQuote] = Field(min_length=2, max_length=2)


class GapItem(BaseModel):
    kind: GapKind
    question_id: str | None = None
    question: str | None = None
    detail: str
    severity: Priority


class FreshnessWarning(BaseModel):
    source_id: str
    kind: FreshnessKind
    detail: str
    age_days: int | None = None


class ActionItem(BaseModel):
    rank: int
    action: str
    reason: str
    priority: Priority
    question_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    mode: AnalysisMode
    goal: str
    questions_analyzed: int
    coverage_percent: int = Field(ge=0, le=100)
    summary: str
    disclaimer: str
    sources: list[SourceRecord]
    coverage: list[QuestionCoverage]
    unanswered_questions: list[str] = Field(default_factory=list)
    gaps: list[GapItem] = Field(default_factory=list)
    conflicts: list[PossibleConflict] = Field(default_factory=list)
    freshness_warnings: list[FreshnessWarning] = Field(default_factory=list)
    actions: list[ActionItem] = Field(default_factory=list)
    inaccessible_source_ids: list[str] = Field(default_factory=list)
    analysis_method: str
    notes: list[str] = Field(default_factory=list)
    analyzed_at: datetime
