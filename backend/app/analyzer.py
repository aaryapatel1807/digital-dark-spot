"""Deterministic analysis engine for /api/analyze.

No LLM output ever becomes a finding here. The engine:
1. Scores every sentence of every accessible source against each
   question by content-token overlap (transparent, reproducible).
2. Marks coverage covered / partial / not_found with fixed
   thresholds (0.50 / 0.25), and keeps the best sentence per
   supporting source as evidence.
3. Flags possible conflicts two ways, both shown with quotes:
   - numeric: two sources give different money / percent / year /
     date values for the same question;
   - stance: one source's passage denies a question term that
     another source's passage affirms.
   Both are labelled "possible" — the engine does not adjudicate.
4. Warns on stale (>365 days) and undated sources; undated is
   never guessed.
5. Builds gaps and a prioritized verify-next action list from the
   computed results only.
6. Runs a final validation sweep: every source ID must exist, every
   quote must be a substring of its source's collected text. Any
   item that fails is dropped and noted, never shipped.

Thresholds and word lists are module constants so a reviewer can
audit them in one place.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone

from .analysis_schemas import (
    ActionItem,
    AnalysisMode,
    AnalysisResponse,
    EvidenceQuote,
    FreshnessWarning,
    GapItem,
    PossibleConflict,
    QuestionCoverage,
    SourceRecord,
)
from .collector import CollectedSource
from .config import get_settings
from .groq_client import derive_questions_with_groq

COVERED_THRESHOLD = 0.50
PARTIAL_THRESHOLD = 0.25
# Partial coverage additionally needs at least two matched tokens:
# a single shared word (often just the topic word, e.g. "year" in a
# renewal question) must not make a question look half-answered.
PARTIAL_MIN_MATCHED = 2
QUOTE_MAX_CHARS = 500
# NOTE: evidence used to be capped at 5 passages per question, but
# supporting_source_ids was not capped — so a 6th supporting source
# got a matrix dot whose drawer showed "supports none of the checked
# questions". Citations must cover every supporting source, so there
# is no evidence cap now; the bound is the input cap (20 sources).

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "of", "to", "in", "on", "for", "with", "and", "or", "by", "at",
    "from", "as", "it", "its", "this", "that", "these", "those",
    "what", "who", "when", "where", "how", "which", "whom", "whose",
    "do", "does", "did", "can", "could", "should", "would", "will",
    "i", "you", "he", "she", "we", "they", "his", "her", "their",
    "am", "an", "not", "no", "yes", "if", "then", "than", "so",
    "about", "into", "over", "under", "between", "through", "during",
    "there", "here", "all", "any", "some", "such", "own", "same",
}

_DENY_CUES = {
    "not", "never", "no", "false", "incorrect", "wrong", "denies",
    "denied", "disputes", "disputed", "refutes", "contradicts",
    "isn't", "wasn't", "doesn't", "don't", "cannot", "can't",
    "fails", "failed", "without", "none",
}

_NUMBER_PATTERNS = [
    # Rs./INR matter in the Indian scholarship context the demo uses:
    # "Rs. 10000" previously produced no money value at all, so a real
    # fee disagreement was silently missed. Lakh/crore words are still
    # NOT parsed — see the audit report limitation.
    ("money", re.compile(r"(?:₹|\$|€|£|Rs\.?|INR)\s?\d[\d,]*(?:\.\d+)?", re.I)),
    ("percent", re.compile(r"\d[\d,]*(?:\.\d+)?\s?%")),
    ("year", re.compile(r"\b(?:19|20)\d{2}\b")),
    ("date", re.compile(r"\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}\b", re.I)),
]


@dataclass
class _ScoredPassage:
    source_id: str
    sentence: str
    score: float
    matched: int


def _stem(word: str) -> str:
    """Light plural folding so "dates" matches "date". Applied to both
    sides, so it can only ever merge forms, never invent a term."""
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {_stem(w) for w in words if w not in _STOPWORDS}


# Tight, bidirectional synonym pairs for the words research questions
# most often phrase differently from sources. This only ever SELECTS
# sentences; every quote it surfaces is still verified verbatim.
_SYNONYMS: dict[str, set[str]] = {
    "deadline": {"date"},
    "date": {"deadline"},
    "eligible": {"eligibility"},
    "eligibility": {"eligible"},
    "amount": {"awarded", "award"},
    "awarded": {"amount", "award"},
    "award": {"amount", "awarded"},
    "apply": {"application"},
    "application": {"apply"},
    "renew": {"renewal"},
    "renewal": {"renew"},
    "cost": {"fee", "price"},
    "fee": {"cost", "price"},
    "price": {"cost", "fee"},
}


_ABBREV_TAIL = re.compile(
    r"(?:^|\s)(?:Rs|Dr|Mr|Mrs|Ms|St|Vs|etc|approx|No|Fig|Prof|Sr|Jr|Inc|Ltd|Co|e\.g|i\.e|[A-Z])\.$",
    re.I,
)


def _sentences(text: str) -> list[str]:
    """Split into sentences without severing abbreviations.

    The old splitter broke on every period, so "Rs. 10000" became two
    fragments — "The scholarship fee is Rs." and "10000 per year…" —
    and the fee sentence carried no number at all, which silently
    killed numeric conflict detection for Rs. amounts. A boundary
    after a known abbreviation (Rs., Dr., e.g., a single initial)
    is not a sentence end. Quotes stay verbatim substrings: nothing
    here rewrites the text, it only chooses where to cut.
    """
    parts: list[str] = []
    start = 0
    for match in re.finditer(r"[.!?…]\s+|\n+", text):
        boundary = match.group(0)
        if "\n" not in boundary and _ABBREV_TAIL.search(text[: match.start() + 1]):
            continue
        parts.append(text[start : match.end()])
        start = match.end()
    parts.append(text[start:])
    out: list[str] = []
    for part in parts:
        sentence = part.strip()
        if len(sentence) >= 15 and len(_tokens(sentence)) >= 2:
            out.append(sentence[:QUOTE_MAX_CHARS])
    return out


def _score(question_tokens: set[str], sentence_tokens: set[str]) -> tuple[float, int]:
    """Fraction of question terms found in the sentence, counting a
    term as found when it or a tight synonym appears."""
    if not question_tokens:
        return 0.0, 0
    matched = sum(
        1
        for token in question_tokens
        if token in sentence_tokens or _SYNONYMS.get(token, set()) & sentence_tokens
    )
    return matched / len(question_tokens), matched


def _supports(score: float, matched: int) -> bool:
    """A passage counts as evidence only if it really addresses the
    question: a high overlap, or a moderate overlap on two or more
    distinct question terms."""
    return score >= COVERED_THRESHOLD or (
        score >= PARTIAL_THRESHOLD and matched >= PARTIAL_MIN_MATCHED
    )


def _best_passages(
    question_tokens: set[str],
    collected: list[CollectedSource],
    sentences_cache: dict[str, list[str]],
    tokens_cache: dict[str, set[str]],
) -> list[_ScoredPassage]:
    """Best supporting passage per source, with per-run caches.

    Sentence splitting and tokenization depend only on the source
    text, not on the question, so recomputing them for every question
    was pure waste (questions × sources × sentences). The caches
    live for one analyze() run only and never change a score: the
    same sentence always tokenizes to the same set.
    """
    scored: list[_ScoredPassage] = []
    for item in collected:
        if item.record.fetch_status != "ok" or not item.text:
            continue
        sentences = sentences_cache.get(item.record.id)
        if sentences is None:
            sentences = _sentences(item.text)
            sentences_cache[item.record.id] = sentences
        best: _ScoredPassage | None = None
        for sentence in sentences:
            tokens = tokens_cache.get(sentence)
            if tokens is None:
                tokens = _tokens(sentence)
                tokens_cache[sentence] = tokens
            score, matched = _score(question_tokens, tokens)
            if score > 0 and (best is None or score > best.score):
                best = _ScoredPassage(item.record.id, sentence, score, matched)
        if best is not None and _supports(best.score, best.matched):
            scored.append(best)
    scored.sort(key=lambda p: -p.score)
    return scored


def _numbers(sentence: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for kind, pattern in _NUMBER_PATTERNS:
        for match in pattern.finditer(sentence):
            value = re.sub(r"[\s,]", "", match.group(0)).lower()
            found.append((kind, value))
    return found


def _numeric_conflict(
    question_id: str, question: str, passages: list[_ScoredPassage]
) -> PossibleConflict | None:
    seen: dict[tuple[str, str], _ScoredPassage] = {}
    for passage in passages:
        for kind, value in _numbers(passage.sentence):
            seen.setdefault((kind, value), passage)
    by_kind: dict[str, dict[str, _ScoredPassage]] = {}
    for (kind, value), passage in seen.items():
        by_kind.setdefault(kind, {})[value] = passage
    for kind, values in by_kind.items():
        distinct = [p for v, p in values.items()]
        sources = {p.source_id for p in distinct}
        if len(distinct) >= 2 and len(sources) >= 2:
            first = distinct[0]
            second = next(p for p in distinct if p.source_id != first.source_id)
            return PossibleConflict(
                question_id=question_id,
                question=question,
                detail=(
                    f"Two sources give different {kind} values for this "
                    "question. This is flagged as a possible conflict, not "
                    "a contradiction: the values may describe different "
                    "things. Verify against the official source."
                ),
                values=[
                    EvidenceQuote(source_id=first.source_id, quote=first.sentence),
                    EvidenceQuote(source_id=second.source_id, quote=second.sentence),
                ],
            )
    return None


def _stance_conflict(
    question_id: str, question: str, question_tokens: set[str],
    passages: list[_ScoredPassage],
) -> PossibleConflict | None:
    denying: _ScoredPassage | None = None
    affirming: _ScoredPassage | None = None
    deny_stems = {_stem(cue) for cue in _DENY_CUES}
    for passage in passages:
        words = [_stem(w) for w in re.findall(r"[a-z']+", passage.sentence.lower())]
        denies = False
        for i, word in enumerate(words):
            if word in question_tokens:
                window = words[max(0, i - 3):i]
                if any(cue in window for cue in deny_stems):
                    denies = True
                    break
        if denies and denying is None:
            denying = passage
        if not denies and affirming is None:
            affirming = passage
    if denying and affirming and denying.source_id != affirming.source_id:
        return PossibleConflict(
            question_id=question_id,
            question=question,
            detail=(
                "One source's passage denies a term another source's "
                "passage affirms for this question. This is flagged as a "
                "possible conflict, not a contradiction — check both "
                "quotes in context."
            ),
            values=[
                EvidenceQuote(source_id=affirming.source_id, quote=affirming.sentence),
                EvidenceQuote(source_id=denying.source_id, quote=denying.sentence),
            ],
        )
    return None


def derive_questions(
    goal: str, user_questions: list[str] | None
) -> tuple[list[tuple[str, str, str]], str, list[str]]:
    """Return [(question_id, text, origin)] plus method and notes.

    User questions are used verbatim. Otherwise Groq may propose
    questions when a key is configured; templates are the fallback.
    """
    notes: list[str] = []
    if user_questions:
        questions = [(f"Q{i + 1}", q, "user") for i, q in enumerate(user_questions)]
        return questions, "deterministic", notes
    groq_questions = derive_questions_with_groq(goal)
    if groq_questions:
        questions = [(f"Q{i + 1}", q, "derived") for i, q in enumerate(groq_questions)]
        return questions, "deterministic+groq_questions", notes
    if get_settings().groq_configured:
        notes.append("Groq question derivation failed; template questions used instead.")
    goal_text = goal.strip().rstrip("?")
    if goal.strip().endswith("?"):
        templates = [goal.strip()]
    else:
        templates = []
    templates += [
        f"What is {goal_text}?",
        f"Who is eligible for {goal_text}?",
        f"What are the key dates and deadlines for {goal_text}?",
        f"What does {goal_text} require or cost?",
        f"How does {goal_text} work, step by step?",
        f"What is missing or uncertain about {goal_text}?",
    ]
    seen: list[str] = []
    for template in templates:
        if template not in seen:
            seen.append(template)
    questions = [(f"Q{i + 1}", q, "derived") for i, q in enumerate(seen[:6])]
    return questions, "deterministic", notes


def _normalize_for_match(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _validate(
    response: AnalysisResponse, texts: dict[str, str]
) -> tuple[AnalysisResponse, list[str]]:
    """Drop any reference or quote that does not check out. Never crash."""
    notes: list[str] = []
    valid_ids = {s.id for s in response.sources}

    def quote_ok(source_id: str, quote: str) -> bool:
        full = texts.get(source_id)
        if full is None:
            return False
        return _normalize_for_match(quote) in _normalize_for_match(full)

    coverage: list[QuestionCoverage] = []
    for item in response.coverage:
        supporting = [s for s in item.supporting_source_ids if s in valid_ids]
        evidence = [e for e in item.evidence if e.source_id in valid_ids and quote_ok(e.source_id, e.quote)]
        dropped = (len(item.supporting_source_ids) - len(supporting)) + (len(item.evidence) - len(evidence))
        if dropped:
            notes.append(f"Dropped {dropped} unverifiable reference(s) for {item.question_id}.")
        status = item.status
        if not evidence:
            status = "not_found"
            supporting = []
        coverage.append(QuestionCoverage(
            question_id=item.question_id, question=item.question, origin=item.origin,
            status=status, supporting_source_ids=supporting, evidence=evidence,
        ))
    conflicts: list[PossibleConflict] = []
    for conflict in response.conflicts:
        values = [v for v in conflict.values if v.source_id in valid_ids and quote_ok(v.source_id, v.quote)]
        if len(values) < 2:
            notes.append(f"Dropped an unverifiable possible conflict for {conflict.question_id}.")
            continue
        conflicts.append(PossibleConflict(
            question_id=conflict.question_id, question=conflict.question,
            detail=conflict.detail, values=values[:2],
        ))
    unanswered = [c.question for c in coverage if c.status == "not_found"]
    covered = sum(1 for c in coverage if c.status == "covered")
    partial = sum(1 for c in coverage if c.status == "partial")
    total = len(coverage) or 1
    coverage_percent = round(100 * (covered + 0.5 * partial) / total)
    gaps = [g for g in response.gaps if g.question_id is None or g.question_id in {c.question_id for c in coverage}]
    actions = []
    for action in response.actions:
        actions.append(ActionItem(
            rank=action.rank, action=action.action, reason=action.reason,
            priority=action.priority,
            question_ids=[q for q in action.question_ids if q in {c.question_id for c in coverage}],
            source_ids=[s for s in action.source_ids if s in valid_ids],
        ))
    cleaned = response.model_copy(update={
        "coverage": coverage, "conflicts": conflicts,
        "unanswered_questions": unanswered, "coverage_percent": coverage_percent,
        "gaps": gaps, "actions": actions,
    })
    return cleaned, notes


def analyze(
    goal: str,
    user_questions: list[str] | None,
    collected: list[CollectedSource],
    mode: AnalysisMode,
    disclaimer: str,
) -> AnalysisResponse:
    """Run the deterministic engine over collected sources."""
    settings = get_settings()
    today = datetime.now(timezone.utc).date()
    questions, method, notes = derive_questions(goal, user_questions)
    records: list[SourceRecord] = [c.record for c in collected]
    texts: dict[str, str] = {c.record.id: c.text for c in collected if c.text}
    accessible = [c for c in collected if c.record.fetch_status == "ok" and c.text]
    inaccessible_ids = [c.record.id for c in collected if c.record.fetch_status != "ok"]

    coverage: list[QuestionCoverage] = []
    conflicts: list[PossibleConflict] = []
    gaps: list[GapItem] = []
    sentences_cache: dict[str, list[str]] = {}
    tokens_cache: dict[str, set[str]] = {}
    for question_id, question, origin in questions:
        tokens = _tokens(question)
        passages = _best_passages(tokens, collected, sentences_cache, tokens_cache)
        best = passages[0] if passages else None
        if best is not None and best.score >= COVERED_THRESHOLD:
            status = "covered"
        elif best is not None and best.score >= PARTIAL_THRESHOLD and best.matched >= PARTIAL_MIN_MATCHED:
            status = "partial"
        else:
            status = "not_found"
        supporting = [p.source_id for p in passages]
        evidence = [EvidenceQuote(source_id=p.source_id, quote=p.sentence) for p in passages]
        coverage.append(QuestionCoverage(
            question_id=question_id, question=question, origin=origin,
            status=status, supporting_source_ids=supporting, evidence=evidence,
        ))
        conflict = _numeric_conflict(question_id, question, passages) or _stance_conflict(
            question_id, question, tokens, passages)
        if conflict is not None:
            conflicts.append(conflict)
        if status == "not_found":
            gaps.append(GapItem(
                kind="unanswered", question_id=question_id, question=question,
                detail="No collected source answers this question. That is a gap in these sources, not proof no answer exists.",
                severity="high",
            ))
        elif status == "partial":
            gaps.append(GapItem(
                kind="partial", question_id=question_id, question=question,
                detail="The collected sources touch on this question but do not fully answer it.",
                severity="medium",
            ))
        if status == "covered":
            supporting_records = {c.record.id: c.record for c in collected if c.record.id in supporting}
            if len(supporting) == 1:
                gaps.append(GapItem(
                    kind="single_source", question_id=question_id, question=question,
                    detail="Only one source covers this question. Corroborate it before relying on it.",
                    severity="low",
                ))
            fresh = [
                r for r in supporting_records.values()
                if r.date_status == "known" and r.published_date
                and (today - r.published_date).days <= settings.freshness_stale_after_days
            ]
            if supporting and not fresh:
                any_stale = any(
                    r.date_status == "known" and r.published_date
                    and (today - r.published_date).days > settings.freshness_stale_after_days
                    for r in supporting_records.values()
                )
                gaps.append(GapItem(
                    kind="stale_only" if any_stale else "undated_only",
                    question_id=question_id, question=question,
                    detail=(
                        "Every source covering this question is stale."
                        if any_stale else
                        "Every source covering this question is undated, so its currency cannot be checked."
                    ),
                    severity="medium" if any_stale else "low",
                ))

    freshness_warnings: list[FreshnessWarning] = []
    for item in accessible:
        record = item.record
        if record.date_status == "unknown":
            freshness_warnings.append(FreshnessWarning(
                source_id=record.id, kind="undated",
                detail="This source carries no publication date, so its freshness cannot be verified.",
            ))
        elif record.published_date:
            age = (today - record.published_date).days
            if age > settings.freshness_stale_after_days:
                freshness_warnings.append(FreshnessWarning(
                    source_id=record.id, kind="stale",
                    detail=f"This source is {age} days old (older than {settings.freshness_stale_after_days} days) and may describe an earlier cycle.",
                    age_days=age,
                ))

    actions: list[ActionItem] = []
    rank = 1
    for gap in gaps:
        if gap.kind == "unanswered":
            actions.append(ActionItem(rank=rank, action=f"Find a source that answers: {gap.question}",
                reason="No collected source addresses this question.", priority="high",
                question_ids=[gap.question_id or ""]))
            rank += 1
    for conflict in conflicts:
        actions.append(ActionItem(rank=rank, action=f"Verify against the official source: {conflict.question}",
            reason="Collected sources disagree; both quotes are shown in the conflict.", priority="high",
            question_ids=[conflict.question_id],
            source_ids=[v.source_id for v in conflict.values]))
        rank += 1
    for gap in gaps:
        if gap.kind == "partial":
            actions.append(ActionItem(rank=rank, action=f"Find a fuller answer for: {gap.question}",
                reason="Current sources only partially answer this question.", priority="medium",
                question_ids=[gap.question_id or ""]))
            rank += 1
    for gap in gaps:
        if gap.kind in ("single_source", "stale_only", "undated_only"):
            verb = {"single_source": "Corroborate", "stale_only": "Re-check against a current source", "undated_only": "Confirm the currency of"}[gap.kind]
            actions.append(ActionItem(rank=rank, action=f"{verb}: {gap.question}",
                reason=gap.detail, priority=gap.severity,
                question_ids=[gap.question_id or ""],
                source_ids=[s for s in next((c.supporting_source_ids for c in coverage if c.question_id == gap.question_id), [])]))
            rank += 1
    for item in collected:
        if item.record.fetch_status != "ok":
            label = item.record.url or item.record.title or item.record.id
            actions.append(ActionItem(rank=rank, action=f"Retry or replace the inaccessible source: {label}",
                reason=item.record.error or "The source could not be read.", priority="medium",
                source_ids=[item.record.id]))
            rank += 1

    covered = sum(1 for c in coverage if c.status == "covered")
    partial = sum(1 for c in coverage if c.status == "partial")
    total = len(coverage) or 1
    coverage_percent = round(100 * (covered + 0.5 * partial) / total)
    unanswered = [c.question for c in coverage if c.status == "not_found"]
    stale_count = sum(1 for w in freshness_warnings if w.kind == "stale")
    undated_count = sum(1 for w in freshness_warnings if w.kind == "undated")
    if not accessible:
        summary = (
            "No sources could be read, so no question could be answered from evidence. "
            "Fix the inaccessible inputs first, then re-run the analysis."
        )
    else:
        summary = (
            f"Across {len(accessible)} accessible source(s) "
            f"({len(inaccessible_ids)} inaccessible), {covered} of {len(coverage)} question(s) "
            f"are covered, {partial} partially, and {len(unanswered)} unanswered. "
            f"Coverage: {coverage_percent}%. {len(conflicts)} possible conflict(s) need verification. "
            f"{stale_count} stale and {undated_count} undated source(s) limit how far dates can be trusted."
        )

    response = AnalysisResponse(
        mode=mode,
        goal=goal,
        questions_analyzed=len(coverage),
        coverage_percent=coverage_percent,
        summary=summary,
        disclaimer=disclaimer,
        sources=records,
        coverage=coverage,
        unanswered_questions=unanswered,
        gaps=gaps,
        conflicts=conflicts,
        freshness_warnings=freshness_warnings,
        actions=actions,
        inaccessible_source_ids=inaccessible_ids,
        analysis_method=method,
        notes=notes,
        analyzed_at=datetime.now(timezone.utc),
    )
    cleaned, validation_notes = _validate(response, texts)
    if validation_notes:
        cleaned = cleaned.model_copy(update={"notes": [*cleaned.notes, *validation_notes]})
    return cleaned
