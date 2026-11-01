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

    @model_validator(mode="after")
    def _check_not_blank(self) -> "PastedText":
        # min_length=1 alone lets "   " through; the collector then
        # normalizes it to empty text and the source counts as neither
        # accessible nor inaccessible. Reject blank text up front.
        if not self.text.strip():
            raise ValueError("Pasted text must contain non-whitespace characters.")
        return self


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
    # Provenance (GapLens 3.0, Phase 6): character offset of the quote
    # in the collected source text, and PDF page when a [Page N]
    # marker precedes it. Both are None when they cannot be computed
    # — never fabricated.
    text_offset: int | None = None
    page: int | None = None


class QuestionCoverage(BaseModel):
    question_id: str
    question: str
    origin: QuestionOrigin
    status: CoverageStatus
    supporting_source_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceQuote] = Field(default_factory=list)
    # GapLens 3.0 entailment + hybrid retrieval (optional, additive):
    # entailment is what the best passage DOES, not a truth verdict:
    # supports / partially_supports / negated_answer / related_but_insufficient /
    # contradicted_by_other_evidence / no_supporting_evidence.
    # semantic_score is a TF-IDF cosine retrieval score (0–1), NOT a
    # probability of truth and NOT an embedding similarity.
    entailment: str | None = None
    semantic_score: float | None = None


class PossibleConflict(BaseModel):
    question_id: str
    question: str
    label: Literal["possible conflict"] = "possible conflict"
    detail: str
    values: list[EvidenceQuote] = Field(min_length=2, max_length=2)
    # Temporal classification (GapLens 2.0 stabilization, Task 3).
    # A 2024 amount and a 2026 amount stay visible, but are NOT
    # presented as a genuine same-period contradiction: they are
    # "different_period". When period/group/scope cannot be told
    # apart, the finding is "uncertain" and must be verified.
    classification: Literal[
        "same_period", "different_period", "different_conditions",
        "different_scope", "uncertain",
    ] = "uncertain"
    classification_note: str | None = None


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


class SuggestedQuestion(BaseModel):
    question_id: str
    question: str
    category: str
    priority: Priority = "medium"
    origin: Literal["suggested"] = "suggested"
    reason: str
    coverage_status: CoverageStatus = "not_found"


class StructuredClaim(BaseModel):
    subject: str
    predicate: str = "value"
    value: str | None = None
    unit: str | None = None
    period: str | None = None
    conditions: list[str] = Field(default_factory=list)
    scope: list[str] = Field(default_factory=list)
    negated: bool = False
    source_id: str
    quote: str


class ContextualConflict(BaseModel):
    question_id: str
    question: str
    classification: Literal[
        "direct_contradiction", "temporal_difference", "conditional_difference",
        "scope_difference", "partial_disagreement", "insufficient_context",
    ]
    explanation: str
    claim_a: StructuredClaim
    claim_b: StructuredClaim


class SemanticAnalysis(BaseModel):
    enabled: bool = True
    method: str = "hybrid_concept_tfidf"
    model: str | None = None


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
    # GapLens 3.0, all optional and additive: old frontends ignore them.
    semantic_analysis: SemanticAnalysis = SemanticAnalysis()
    suggested_questions: list[SuggestedQuestion] = Field(default_factory=list)
    contextual_conflicts: list[ContextualConflict] = Field(default_factory=list)
    analysis_limitations: list[str] = Field(default_factory=list)
