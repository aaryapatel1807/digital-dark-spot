"""Evidence integrity regressions for the 2.0 workspace."""
from app.analyzer import _validate
from app.analysis_schemas import EvidenceQuote
from tests.test_analyzer import _src, _run


def test_currency_aliases_and_scales_are_not_conflicts():
    for amount in ("INR 10000", "₹10,000.00", "Rs. 0.1 lakh"):
        result = _run(["What is the scholarship fee?"], [
            _src("S1", "The scholarship fee is Rs. 10000 per year."),
            _src("S2", f"The scholarship fee is {amount} per year."),
        ])
        assert not result.conflicts


def test_validation_rebuilds_findings_after_removing_evidence():
    source = _src("S1", "Students are eligible when family income is below the limit.")
    result = _run(["Who is eligible?"], [source])
    result.coverage[0].evidence = [EvidenceQuote(source_id="S1", quote="Invented evidence.")]
    cleaned, notes = _validate(result, {"S1": source.text})
    assert notes
    assert cleaned.coverage_percent == 0
    assert {g.kind for g in cleaned.gaps} == {"unanswered"}
    assert cleaned.actions[0].priority == "high"
    assert "0 of 1" in cleaned.summary


def test_validation_removes_support_without_a_valid_quote():
    sources = [_src("S1", "Students are eligible when income is below the limit."),
               _src("S2", "Students are eligible when income is below another limit.")]
    result = _run(["Who is eligible?"], sources)
    result.coverage[0].evidence[1].quote = ""
    cleaned, _ = _validate(result, {s.record.id: s.text for s in sources})
    assert cleaned.coverage[0].supporting_source_ids == ["S1"]
    assert any(g.kind == "single_source" for g in cleaned.gaps)


def test_all_inaccessible_summary_says_nothing_could_be_read():
    result = _run(["What is the secret?"], [
        _src("S1", "", status="blocked"),
        _src("S2", "", status="failed"),
    ])
    assert result.coverage_percent == 0
    assert "No sources could be read" in result.summary
    assert "Fix the inaccessible inputs first" in result.summary


def test_identical_sources_are_flagged_not_corroboration():
    text = "Students are eligible when family income is below the limit."
    result = _run(["Who is eligible?"], [_src("S1", text), _src("S2", text)])
    assert any("S1 and S2 contain identical text" in n for n in result.notes)
    assert any("not independent corroboration" in n for n in result.notes)
    # Distinct text must not be flagged.
    result2 = _run(["Who is eligible?"], [
        _src("S1", text),
        _src("S2", "Students are eligible when family income is below another limit."),
    ])
    assert not any("identical text" in n for n in result2.notes)


def test_mixed_old_and_undated_sources_are_described_accurately():
    from datetime import date, timedelta
    result = _run(["Who is eligible?"], [
        _src("S1", "Students are eligible when income is below the limit.", date.today() - timedelta(days=800)),
        _src("S2", "Students are eligible when income is below another limit."),
    ])
    gap = next(g for g in result.gaps if g.kind == "stale_only")
    assert "undated" in gap.detail
