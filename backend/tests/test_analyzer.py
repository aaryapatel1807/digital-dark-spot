"""Engine checks for the deterministic analyzer.

Every assertion here is about honesty, not just shape:
- quotes must be substrings of the source text they cite;
- a fabricated quote is dropped by the validation sweep;
- "not found" (no answer in the sources) stays distinct from
  "nonexistent" (a host that does not resolve, covered in the
  fetcher tests);
- undated sources are reported as unknown, never guessed.
"""

from datetime import date, timedelta

import pytest

from app.analysis_schemas import (
    AnalysisResponse,
    EvidenceQuote,
    QuestionCoverage,
    SourceRecord,
)
from app.analyzer import _validate, analyze
from app.collector import CollectedSource
from app.sample_analysis import build_sample_analysis_response


@pytest.fixture(autouse=True)
def _no_groq(monkeypatch):
    """Keep engine tests hermetic: never call Groq, even if a key is set."""
    monkeypatch.setattr("app.analyzer.derive_questions_with_groq", lambda goal: None)


def _src(source_id, text, published=None, status="ok"):
    return CollectedSource(
        record=SourceRecord(
            id=source_id,
            kind="pasted_text",
            title=f"Source {source_id}",
            fetch_status=status,
            date_status="known" if published else "unknown",
            published_date=published,
            text_excerpt=text[:1000] if text else None,
            text_length=len(text) if text else 0,
            error=None if status == "ok" else "simulated failure",
        ),
        text=text,
    )


def _run(questions, sources):
    return analyze("Scholarship application", questions, sources, "live", "test disclaimer")


def test_covered_partial_and_not_found():
    sources = [
        _src("S1", "Students are eligible when family income is below the limit. The last date to apply is 31 December 2026."),
        _src("S2", "The award covers tuition fees and books for selected students."),
    ]
    result = _run(
        ["Who is eligible?", "What are the key dates and deadlines?", "What renews the scholarship next year?"],
        sources,
    )
    by_id = {c.question_id: c for c in result.coverage}
    assert by_id["Q1"].status == "covered"
    assert by_id["Q2"].status == "covered"
    assert by_id["Q3"].status == "not_found"
    assert "What renews the scholarship next year?" in result.unanswered_questions
    assert any(g.kind == "unanswered" and g.severity == "high" for g in result.gaps)


def test_single_shared_word_is_not_partial():
    # Only the topic word "year" overlaps: must stay not_found.
    sources = [_src("S1", "Family income up to a limit per year is eligible for applicants.")]
    result = _run(["What renews the scholarship next year?"], sources)
    assert result.coverage[0].status == "not_found"


def test_numeric_conflict_with_verified_quotes():
    sources = [
        _src("S1", "Family income up to ₹2,50,000 per year is eligible for the scholarship."),
        _src("S2", "Students are eligible when family income limit is ₹2,00,000 per year."),
    ]
    result = _run(["Who is eligible?"], sources)
    assert len(result.conflicts) == 1
    conflict = result.conflicts[0]
    assert conflict.label == "possible conflict"
    assert len(conflict.values) == 2
    texts = {"S1": sources[0].text, "S2": sources[1].text}
    for value in conflict.values:
        assert value.quote in texts[value.source_id]


def test_bare_number_conflict_cgpa():
    # The judge-facing case: CGPA carries no currency/unit marker,
    # yet 7.0 vs 7.5 for the same renewal question must still flag.
    sources = [
        _src("S1", "Renewal of the scholarship requires a CGPA of 7.0 or above."),
        _src("S2", "Renewal of the scholarship requires students to maintain a CGPA of 7.5 or above."),
    ]
    result = _run(["What CGPA is required for renewal?"], sources)
    assert result.coverage[0].status == "covered"
    assert len(result.conflicts) == 1
    assert result.conflicts[0].label == "possible conflict"
    assert {v.source_id for v in result.conflicts[0].values} == {"S1", "S2"}


def test_bare_number_same_value_is_not_a_conflict():
    sources = [
        _src("S1", "Renewal of the scholarship requires a CGPA of 7.0 or above."),
        _src("S2", "Students must maintain a CGPA of 7.0 for renewal of the scholarship."),
    ]
    result = _run(["What CGPA is required for renewal?"], sources)
    assert not result.conflicts


def test_no_official_source_alert():
    # Pasted texts have no host, so they can never count as official.
    sources = [_src("S1", "Students are eligible when family income is below the limit.")]
    result = _run(["Who is eligible?"], sources)
    assert "No official source was reviewed in this run." in result.summary
    assert any(a.action == "Find an official source for this topic" and a.priority == "high" for a in result.actions)


def test_renewal_phrased_as_continue_is_covered():
    # The brief's semantic example: a question about renewal must
    # match a passage about continuing support in later years.
    # Synonyms only SELECT sentences; the quote is still verified.
    sources = [
        _src("S1", "Recipients may continue receiving financial support in subsequent academic years subject to maintaining eligibility."),
    ]
    result = _run(["Can this scholarship be renewed?"], sources)
    assert result.coverage[0].status == "covered"


def test_stance_conflict_with_verified_quotes():
    sources = [
        _src("S1", "Students are eligible for the scholarship when income is below the limit."),
        _src("S2", "Students are not eligible for the scholarship in the second year."),
    ]
    result = _run(["Who is eligible for the scholarship?"], sources)
    assert len(result.conflicts) == 1
    texts = {"S1": sources[0].text, "S2": sources[1].text}
    for value in result.conflicts[0].values:
        assert value.quote in texts[value.source_id]


def test_all_quotes_are_substrings_of_their_sources():
    sources = [
        _src("S1", "The last date to apply is 31 December 2026. Apply online through the national portal today."),
        _src("S2", "The awarded amount is ₹12,000 per year for selected students in the programme."),
    ]
    result = _run(
        ["When is the last date to apply?", "How much is awarded?", "Who is eligible?"],
        sources,
    )
    texts = {s.record.id: s.text for s in sources}
    for item in result.coverage:
        for evidence in item.evidence:
            assert evidence.quote in texts[evidence.source_id]
    for conflict in result.conflicts:
        for value in conflict.values:
            assert value.quote in texts[value.source_id]


def test_evidence_covers_every_supporting_source():
    """Regression: evidence used to be capped at 5 while
    supporting_source_ids was not, so a 6th supporting source got a
    matrix dot whose drawer showed no passage. Every supporting
    source must have a citation, however many there are."""
    sources = [
        _src(f"S{i}", f"The scholarship fee is Rs. 10000 per year for students in group {i}.")
        for i in range(1, 7)
    ]
    result = _run(["What is the scholarship fee?"], sources)
    row = result.coverage[0]
    assert row.supporting_source_ids == [f"S{i}" for i in range(1, 7)]
    assert [e.source_id for e in row.evidence] == row.supporting_source_ids
    texts = {s.record.id: s.text for s in sources}
    for evidence in row.evidence:
        assert evidence.quote in texts[evidence.source_id]


def test_validation_drops_fabricated_quote_and_demotes():
    good = _src("S1", "Students are eligible when family income is below the limit.")
    base = _run(["Who is eligible?"], [good])
    tampered = base.model_copy(update={
        "coverage": [
            QuestionCoverage(
                question_id="Q1", question="Who is eligible?", origin="user",
                status="covered", supporting_source_ids=["S1", "S99"],
                evidence=[
                    EvidenceQuote(source_id="S1", quote="Students are eligible when family income is below the limit."),
                    EvidenceQuote(source_id="S1", quote="The minister confirmed a brand new rule yesterday."),
                ],
            )
        ],
    })
    cleaned, notes = _validate(tampered, {"S1": good.text})
    assert cleaned.coverage[0].supporting_source_ids == ["S1"]
    assert len(cleaned.coverage[0].evidence) == 1
    assert notes  # The drop is reported, not silent.


def test_freshness_stale_and_undated_warnings():
    today = date.today()
    sources = [
        _src("S1", "Students are eligible when family income is below the limit.", published=today - timedelta(days=800)),
        _src("S2", "The last date to apply is 31 December 2026.", published=None),
    ]
    result = _run(["Who is eligible?", "When is the last date to apply?"], sources)
    kinds = {w.source_id: w.kind for w in result.freshness_warnings}
    assert kinds["S1"] == "stale"
    assert kinds["S2"] == "undated"
    assert result.freshness_warnings[0].age_days is not None


def test_single_source_and_stale_only_gaps():
    today = date.today()
    sources = [_src("S1", "The awarded amount is ₹12,000 per year for selected students.", published=today - timedelta(days=800))]
    result = _run(["How much is awarded?"], sources)
    kinds = {g.kind for g in result.gaps}
    assert "single_source" in kinds
    assert "stale_only" in kinds


def test_actions_are_ranked_with_unanswered_first():
    sources = [_src("S1", "Students are eligible when family income is below the limit.")]
    result = _run(["Who is eligible?", "What renews the scholarship next year?"], sources)
    ranks = [a.rank for a in result.actions]
    assert ranks == sorted(ranks) == list(range(1, len(ranks) + 1))
    assert result.actions[0].priority == "high"
    assert "renews" in result.actions[0].action


def test_inaccessible_sources_are_marked_not_dropped():
    sources = [
        _src("S1", "Students are eligible when family income is below the limit."),
        _src("S2", None, status="not_found"),
        _src("S3", None, status="nonexistent"),
    ]
    result = _run(["Who is eligible?"], sources)
    assert result.inaccessible_source_ids == ["S2", "S3"]
    by_id = {s.id: s for s in result.sources}
    assert by_id["S2"].fetch_status == "not_found"
    assert by_id["S3"].fetch_status == "nonexistent"
    assert by_id["S2"].fetch_status != by_id["S3"].fetch_status
    assert any("S2" in a.source_ids for a in result.actions)


def test_derived_questions_when_none_given():
    result = analyze("Scholarship application", None, [_src("S1", "Students are eligible.")], "live", "test")
    assert result.questions_analyzed >= 1
    assert all(c.origin == "derived" for c in result.coverage)


def test_sample_mode_is_labelled_and_honest():
    result = build_sample_analysis_response()
    assert result.mode == "offline_sample"
    assert "Demo data only" in result.disclaimer
    assert all(s.is_sample is True for s in result.sources)
    assert all(s.url is None for s in result.sources)
    assert result.coverage_percent == 86
    assert any(g.kind == "unanswered" for g in result.gaps)
    assert len(result.conflicts) == 1  # The income-limit difference.
    assert {w.kind for w in result.freshness_warnings} == {"stale", "undated"}
    texts = {
        "S1": "Family income up to ₹2,50,000 per year is eligible.",
        "S2": "family income limit is ₹2,00,000 per year",
    }
    for value in result.conflicts[0].values:
        assert value.source_id in texts
