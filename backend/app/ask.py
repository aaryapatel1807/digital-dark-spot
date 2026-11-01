"""Ask GapLens — evidence-grounded follow-up assistant (GapLens 2.0, Step 5).

Deliberately NOT an LLM assistant: the answer is built only from
the submitted report's own validated evidence (coverage quotes,
gaps, conflicts, actions). No new facts are written, so no
hallucinated citation is possible:
- Citations are taken from the report's coverage evidence only,
  and each citation's source ID must exist in the report.
- If no evidence passage scores at least partial coverage for the
  question, the answer says plainly that it cannot answer from
  this evidence, and points at the report's gaps/actions instead
  of inventing an answer.
- Conflicts are surfaced when they share a question with the
  follow-up, so a one-sided answer is never given where sources
  disagree.
"""

from __future__ import annotations

from .analysis_schemas import AnalysisResponse, EvidenceQuote
from .analyzer import _score, _tokens


def answer_question(question: str, result: AnalysisResponse) -> dict:
    q_tokens = _tokens(question)
    scored: list[tuple[float, int, EvidenceQuote]] = []
    seen: set[str] = set()
    for row in result.coverage:
        for evidence in row.evidence:
            if evidence.quote in seen:
                continue
            seen.add(evidence.quote)
            e_tokens = _tokens(evidence.quote)
            score, matched = _score(q_tokens, e_tokens, evidence.quote)
            if score > 0 and matched >= 1:
                scored.append((score, matched, evidence))
    scored.sort(key=lambda item: (-item[0], -item[1]))
    # Partial threshold, same as the engine: a single shared topic
    # word must not count as an answer.
    citations = [
        item[2] for item in scored
        if (item[0] >= 0.25 and item[1] >= 2) or item[0] >= 0.50
    ][:3]
    valid_ids = {s.id for s in result.sources}
    citations = [c for c in citations if c.source_id in valid_ids]
    related_conflicts = []
    for conflict in result.conflicts:
        c_tokens = _tokens(conflict.question)
        if c_tokens and q_tokens and len(c_tokens & q_tokens) / len(c_tokens | q_tokens) >= 0.25:
            related_conflicts.append(conflict.question)
    related_gaps = [g.question for g in result.gaps if g.question]
    if not citations:
        answer = (
            "I can't answer that from this investigation's evidence. "
            "None of the passages in this report covers your question, "
            "so any answer would be a guess. Check the report's gaps "
            "and verify-next list for what to look for in a new source."
        )
        return {
            "question": question,
            "answered": False,
            "answer": answer,
            "citations": [],
            "related_conflict_questions": related_conflicts,
            "related_gap_questions": related_gaps,
            "suggested_actions": [a.action for a in result.actions[:3]],
        }
    quoted = "; ".join(f"{c.source_id}: \u201c{c.quote}\u201d" for c in citations)
    answer = (
        "From the evidence in this report: " + quoted + " "
        "Those passages are the only basis for an answer here — they "
        "show what the sources say, not that the statements are true. "
        "If the passages disagree or only partly answer you, verify "
        "against the original sources before acting."
    )
    if related_conflicts:
        answer += " Note: sources disagree on a related question in this report, so treat any single answer with care."
    return {
        "question": question,
        "answered": True,
        "answer": answer,
        "citations": citations,
        "related_conflict_questions": related_conflicts,
        "related_gap_questions": related_gaps,
        "suggested_actions": [a.action for a in result.actions[:3]],
    }
