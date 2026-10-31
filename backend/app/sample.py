"""Honest offline sample mode.

This is the ONLY sample in the foundation, and it is labelled as a
sample at every layer: the endpoint, the schema (`mode`,
`is_sample`), and the UI banner. It reuses the shape of the earlier
Digital Dark Spot scholarship demo (slots, one renewal gap, income
and document differences) so reviewers can see a complete result,
but every source here is explicitly bundled demo data with no URL —
nothing is presented as a live fetch or a real citation.
"""

from __future__ import annotations

from .schemas import (
    ConflictValue,
    CoverageSlot,
    SampleAnalysis,
    SampleChecklistItem,
    SampleConflict,
    SampleGap,
    SampleSource,
)


def build_sample_analysis() -> SampleAnalysis:
    sources = [
        SampleSource(
            id="S1",
            label="Official scholarship page (demo)",
            kind="official",
            note="Bundled demo source. Not fetched; no real page is claimed.",
        ),
        SampleSource(
            id="S2",
            label="Education blog post (demo)",
            kind="blog",
            note="Bundled demo source. Represents a non-official write-up.",
        ),
        SampleSource(
            id="S3",
            label="Student forum thread (demo)",
            kind="forum",
            note="Bundled demo source. Represents an undated discussion.",
        ),
    ]
    slots = [
        CoverageSlot(slot="eligibility", question="Who is eligible?", status="covered", source_ids=["S1", "S2"]),
        CoverageSlot(slot="deadline", question="When is the last date to apply?", status="covered", source_ids=["S1"]),
        CoverageSlot(slot="amount", question="How much is awarded?", status="covered", source_ids=["S1", "S2"]),
        CoverageSlot(slot="documents", question="Which documents are required?", status="partial", source_ids=["S1", "S2"]),
        CoverageSlot(slot="how_to_apply", question="How do you apply?", status="covered", source_ids=["S1"]),
        CoverageSlot(slot="renewal", question="What renews the scholarship next year?", status="gap", source_ids=[]),
        CoverageSlot(slot="contact", question="Who do you contact with questions?", status="covered", source_ids=["S1"]),
    ]
    return SampleAnalysis(
        topic="Scholarship application (demo)",
        coverage_percent=86,  # 6 of 7 slots have at least one demo source.
        sources=sources,
        slots=slots,
        gaps=[
            SampleGap(
                slot="renewal",
                title="Potential gap: renewal conditions not found",
                detail=(
                    "None of the demo sources state what a student must do to "
                    "keep the scholarship in a second year. That is a gap in "
                    "these sources, not proof that no renewal rule exists."
                ),
                severity="high",
            )
        ],
        conflicts=[
            SampleConflict(
                slot="eligibility",
                detail=(
                    "Two demo sources give different family-income limits. "
                    "GapLens does not pick a winner; verify against the "
                    "official source."
                ),
                values=[
                    ConflictValue(source_id="S1", value="₹2,50,000", quote="Family income up to ₹2,50,000 per year."),
                    ConflictValue(source_id="S2", value="₹2,00,000", quote="Income limit is ₹2,00,000 per year."),
                ],
            ),
            SampleConflict(
                slot="documents",
                detail=(
                    "The document lists differ between demo sources. This is "
                    "flagged as a possible conflict, not a contradiction: a "
                    "document missing from one list may simply be omitted there."
                ),
                values=[
                    ConflictValue(source_id="S1", value="Income certificate", quote="Attach income certificate and mark sheet."),
                    ConflictValue(source_id="S2", value="Income proof", quote="Upload income proof and domicile certificate."),
                ],
            ),
        ],
        checklist=[
            SampleChecklistItem(rank=1, action="Ask the official source about renewal conditions", reason="Renewal is the one uncovered slot.", priority="high"),
            SampleChecklistItem(rank=2, action="Confirm the income limit on the official page", reason="Demo sources disagree: ₹2,50,000 vs ₹2,00,000.", priority="high"),
            SampleChecklistItem(rank=3, action="Confirm the full document list", reason="Document lists differ across demo sources.", priority="medium"),
            SampleChecklistItem(rank=4, action="Confirm the deadline against the current cycle", reason="Deadlines go stale fastest; re-check before applying.", priority="medium"),
            SampleChecklistItem(rank=5, action="Find a contact for questions", reason="Covered in the demo, but always verify it still works.", priority="low"),
        ],
    )
