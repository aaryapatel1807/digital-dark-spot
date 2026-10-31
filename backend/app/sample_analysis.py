"""Clearly labelled offline sample mode for POST /api/analyze.

This is NOT the foundation's GET /api/sample (which stays untouched).
It builds an AnalysisResponse from bundled demo texts and runs them
through the SAME deterministic engine as live runs, so the sample
demonstrates real engine behaviour — including a genuine numeric
conflict and a genuine renewal gap — without claiming any real page.

Every sample source has is_sample=True and url=None. Dates are
relative to the analysis day on purpose: one fresh, one stale, one
undated, so the sample also demonstrates freshness warnings. The
disclaimer says plainly that no real scholarship is described.
"""

from __future__ import annotations

from datetime import date, timedelta

from .analysis_schemas import AnalysisResponse, PastedText, SourceRecord
from .analyzer import analyze
from .collector import CollectedSource

_DEMO_DISCLAIMER = (
    "Demo data only. This analysis was NOT fetched from the web and "
    "describes no real scholarship. It shows the shape of a GapLens "
    "result so the interface can be reviewed without an API key."
)


def build_sample_analysis_response(goal: str = "Scholarship application (demo)") -> AnalysisResponse:
    today = date.today()
    demo_texts = [
        (
            "Official scholarship page (demo)",
            "The National Merit Scholarship is open to students who passed class 12 with at least 75 percent marks. "
            "Family income up to ₹2,50,000 per year is eligible. "
            "The last date to apply is 31 December 2026. "
            "Required documents: attach income certificate and mark sheet. "
            "Apply online through the national portal. "
            "For questions, contact the scholarship help desk.",
            today - timedelta(days=30),
        ),
        (
            "Education blog post (demo)",
            "The guide says students are eligible when family income limit is ₹2,00,000 per year. "
            "Required documents include income proof and domicile certificate. "
            "The awarded amount is ₹12,000 per year for selected students.",
            today - timedelta(days=800),
        ),
        (
            "Student forum thread (demo)",
            "Has anyone applied for the National Merit Scholarship? "
            "I submitted my income proof and mark sheet last week. "
            "Nobody in this thread mentions renewal rules for the second term.",
            None,
        ),
    ]
    collected: list[CollectedSource] = []
    for index, (title, text, published) in enumerate(demo_texts, start=1):
        collected.append(
            CollectedSource(
                record=SourceRecord(
                    id=f"S{index}",
                    kind="pasted_text",
                    url=None,
                    title=title,
                    fetch_status="ok",
                    date_status="known" if published else "unknown",
                    published_date=published,
                    text_excerpt=text[:1000],
                    text_length=len(text),
                    error=None,
                    is_sample=True,
                ),
                text=text,
            )
        )
    # The demo questions mirror the foundation sample's slots so the
    # two sample shapes stay comparable.
    questions = [
        "Who is eligible?",
        "When is the last date to apply?",
        "How much is awarded?",
        "Which documents are required?",
        "How do you apply?",
        "What renews the scholarship next year?",
        "Who do you contact with questions?",
    ]
    response = analyze(goal, questions, collected, "offline_sample", _DEMO_DISCLAIMER)
    return response


# Re-exported for callers that build sample inputs directly.
__all__ = ["build_sample_analysis_response", "PastedText"]
