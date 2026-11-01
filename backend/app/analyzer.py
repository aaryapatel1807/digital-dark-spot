"""Deterministic analysis engine for /api/analyze.

No LLM output ever becomes a finding here. The engine:
1. Scores every sentence of every accessible source against each
   question by content-token overlap (transparent, reproducible).
2. Marks coverage covered / partial / not_found with fixed
   thresholds (0.50 / 0.25), and keeps the best sentence per
   supporting source as evidence.
3. Flags possible conflicts two ways, both shown with quotes:
   - numeric: two sources give different money / percent / year /
     date / bare-number values for the same question (bare numbers
     cover scores and counts such as CGPA 7.0 vs 7.5, which carry
     no currency or unit marker);
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
from decimal import Decimal
from dataclasses import dataclass
from datetime import date, datetime, timezone
from urllib.parse import urlparse

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
from .groq_client import derive_questions_with_groq, derive_semantic_terms

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
    # fee disagreement was silently missed. Currency aliases and
    # lakh/crore scales are normalized for comparison, never in quotes.
    ("money", re.compile(r"(?:₹|\$|€|£|Rs\.?|INR)\s?\d[\d,]*(?:\.\d+)?(?:\s*(?:lakhs?|crores?|million|thousand))?", re.I)),
    ("percent", re.compile(r"\d[\d,]*(?:\.\d+)?\s?%")),
    ("year", re.compile(r"\b(?:19|20)\d{2}\b")),
    ("date", re.compile(r"\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}\b", re.I)),
    # Bare numbers last, so money/percent/year/date matches win their
    # spans (see _numbers): a CGPA, score, mark, seat count or other
    # unit-free value still counts as a comparable value, but the
    # same digits are never double-counted as both money and number.
    ("number", re.compile(r"\b\d[\d,]*(?:\.\d+)?\b")),
]


_OFFICIAL_HOSTS = (".gov.in", ".nic.in", ".gov")
_UNIVERSITY_HOSTS = (".ac.in", ".edu", ".edu.in", ".ac.uk")
_NEWS_HOSTS = {
    "bbc.com", "bbc.co.uk", "ndtv.com", "timesofindia.indiatimes.com",
    "indianexpress.com", "thehindu.com", "hindustantimes.com",
    "reuters.com", "apnews.com",
}


def _source_tier(url: str | None) -> str:
    """Trust tier from a source URL host only, never from content.

    official = government host, university = academic host,
    news = a small known-news host list, unknown = everything else
    (including pasted text, which has no host to judge). The tier is
    a label for the reviewer, never a verdict on truth.
    """
    if not url:
        return "unknown"
    host = (urlparse(url).hostname or "").lower()
    host = host[7:] if host.startswith("www.") else host
    if host.endswith(_OFFICIAL_HOSTS):
        return "official"
    if host.endswith(_UNIVERSITY_HOSTS):
        return "university"
    if host in _NEWS_HOSTS:
        return "news"
    return "unknown"


@dataclass
class _ScoredPassage:
    source_id: str
    sentence: str
    score: float
    matched: int


def _stem(word: str) -> str:
    """Light suffix folding so "dates" matches "date" and "continued"
    matches "continuing". Applied to both sides, so it can only ever
    merge forms, never invent a term."""
    if len(word) > 5 and word.endswith("ing"):
        return word[:-3]
    if len(word) > 4 and word.endswith("ed") and not word.endswith("eed"):
        return word[:-2]
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {_stem(w) for w in words if w not in _STOPWORDS}


# Concept clusters (GapLens 2.0, Step 2): words research questions
# most often phrase differently from sources, grouped by meaning.
# This only ever SELECTS sentences; every quote it surfaces is
# still verified verbatim. Clusters are deliberately tight — a
# broad cluster would turn every shared topic word into coverage.
# This is paraphrase-aware matching, NOT embeddings: no local model
# fits the free container, and no new paid API is added.
_CONCEPT_CLUSTERS: list[set[str]] = [
    {"renew", "renewal", "renewed", "renewing", "continue", "continuing", "continued", "extend", "extension"},
    {"eligible", "eligibility", "qualify", "qualified", "qualifying"},
    {"deadline", "date"},
    {"amount", "award", "awarded", "grant", "funding"},
    {"fee", "cost", "price", "tuition", "charges"},
    {"document", "documents", "certificate", "proof", "paperwork"},
    {"apply", "application", "applying", "submit", "submission"},
    {"select", "selection", "selected", "choose", "chosen"},
    {"support", "assistance", "aid"},
    {"college", "university", "institution", "institute"},
    {"job", "employment", "position", "role", "offer"},
    {"scheme", "program", "programme", "initiative"},
    {"process", "procedure", "steps", "step"},
    {"require", "required", "requirement", "requirements", "needed", "necessary"},
    {"marks", "score", "grade"},
    {"contact", "helpline", "helpdesk"},
]
_SYNONYMS: dict[str, set[str]] = {}
for _cluster in _CONCEPT_CLUSTERS:
    _stemmed = {_stem(w) for w in _cluster}
    for _term in _stemmed:
        _SYNONYMS.setdefault(_term, set()).update(_stemmed - {_term})

# Multi-word phrases that carry a concept a single token cannot:
# "open to undergraduate students" means eligible; "last date to
# apply" means deadline. Checked against the sentence text, so a
# phrase match is as verifiable as a token match.
_PHRASE_SYNONYMS: dict[str, set[str]] = {
    "eligible": {"open to"},
    "eligibility": {"open to"},
    "deadline": {"last date"},
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


def _score(
    question_tokens: set[str],
    sentence_tokens: set[str],
    sentence_text: str = "",
    expanded: dict[str, set[str]] | None = None,
) -> tuple[float, int]:
    """Fraction of question terms found in the sentence, counting a
    term as found when it, a concept-cluster synonym, a Groq-proposed
    equivalent term, or a phrase synonym appears. Expanded terms are
    alternative surface forms for a question term, never new
    requirements — the denominator stays the original question terms."""
    if not question_tokens:
        return 0.0, 0
    text = sentence_text.lower()
    matched = 0
    weighted = 0.0
    for token in question_tokens:
        if token in sentence_tokens:
            matched += 1
            weighted += 1.0
        elif _SYNONYMS.get(token, set()) & sentence_tokens:
            matched += 1
            weighted += 1.0
        elif expanded and expanded.get(token, set()) & sentence_tokens:
            matched += 1
            weighted += 1.0
        elif any(phrase in text for phrase in _PHRASE_SYNONYMS.get(token, set())):
            # Phrase matches are weaker than token matches (weight 0.5):
            # a sentence that merely says "open to students" must not
            # outrank a sentence that actually states the eligibility
            # terms when both are candidates for the same question.
            # This kept the demo's income conflict intact: the income
            # sentence (weight 1.0) still beats the opening sentence.
            matched += 1
            weighted += 0.5
    return weighted / len(question_tokens), matched


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
    expanded: dict[str, set[str]] | None = None,
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
            score, matched = _score(question_tokens, tokens, sentence, expanded)
            if score > 0 and (best is None or score > best.score):
                best = _ScoredPassage(item.record.id, sentence, score, matched)
        if best is not None and _supports(best.score, best.matched):
            scored.append(best)
    scored.sort(key=lambda p: -p.score)
    return scored


def _numbers(sentence: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    claimed_spans: list[tuple[int, int]] = []
    for kind, pattern in _NUMBER_PATTERNS:
        for match in pattern.finditer(sentence):
            if kind == "number" and any(
                match.start() < end and start < match.end()
                for start, end in claimed_spans
            ):
                continue
            if kind != "number":
                claimed_spans.append((match.start(), match.end()))
            value = re.sub(r"[\s,]", "", match.group(0)).lower()
            detected_kind = kind
            if kind == "number":
                value = str(Decimal(value).normalize())
            elif kind == "money":
                currency = re.match(r"₹|\$|€|£|rs\.?|inr", value).group()
                currency = "INR" if currency in {"₹", "rs", "rs.", "inr"} else currency
                amount = Decimal(re.search(r"\d+(?:\.\d+)?", value).group())
                scale = next((factor for word, factor in (("lakh", 100000), ("crore", 10000000), ("million", 1000000), ("thousand", 1000)) if word in value), 1)
                value = f"{currency}:{(amount * scale).normalize()}"
                detected_kind = f"money ({currency})"
            found.append((detected_kind, value))
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
    valid_ids = {s.id for s in response.sources if s.fetch_status == "ok"}

    def quote_ok(source_id: str, quote: str) -> bool:
        full = texts.get(source_id)
        if not full or not quote.strip():
            return False
        return _normalize_for_match(quote) in _normalize_for_match(full)

    coverage: list[QuestionCoverage] = []
    for item in response.coverage:
        evidence = [e for e in item.evidence if e.source_id in valid_ids and quote_ok(e.source_id, e.quote)]
        supporting = list(dict.fromkeys(e.source_id for e in evidence))
        dropped = sum(s not in supporting for s in item.supporting_source_ids) + (len(item.evidence) - len(evidence))
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
        if len({v.source_id for v in values}) < 2 or conflict.question_id not in {c.question_id for c in coverage}:
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
    # Dependent findings must be derived from validated evidence, not
    # left behind after a quote or source has been rejected.
    cleaned = _rebuild_findings(cleaned)
    return cleaned, notes


def _rebuild_findings(response: AnalysisResponse) -> AnalysisResponse:
    records = {s.id: s for s in response.sources}
    today = response.analyzed_at.date()
    threshold = get_settings().freshness_stale_after_days
    gaps: list[GapItem] = []
    for row in response.coverage:
        def gap(kind, detail, severity):
            gaps.append(GapItem(kind=kind, question_id=row.question_id,
                                question=row.question, detail=detail, severity=severity))
        if row.status == "not_found":
            gap("unanswered", "No matching evidence was found in the reviewed sources. This does not prove no answer exists.", "high")
        elif row.status == "partial":
            gap("partial", "Only partial keyword coverage was found; inspect the passages for a complete answer.", "medium")
        else:
            sources = [records[s] for s in row.supporting_source_ids]
            if len(sources) == 1:
                gap("single_source", "Only one source covers this question. Corroborate it before relying on it.", "low")
            fresh = [s for s in sources if s.published_date and 0 <= (today - s.published_date).days <= threshold]
            if sources and not fresh:
                old = any(s.published_date and (today - s.published_date).days > threshold for s in sources)
                gap("stale_only" if old else "undated_only",
                    "Supporting sources are old, undated, or future-dated; no current dated evidence was found." if old else
                    "No supporting source has a verifiable current publication date.", "medium" if old else "low")
    actions: list[ActionItem] = []
    verbs = {"unanswered": "Find a source that answers", "partial": "Find a fuller answer for", "single_source": "Corroborate", "stale_only": "Re-check against a current source", "undated_only": "Confirm the currency of"}
    for g in gaps:
        row = next(c for c in response.coverage if c.question_id == g.question_id)
        actions.append(ActionItem(rank=0, action=f"{verbs[g.kind]}: {g.question}", reason=g.detail,
                                  priority=g.severity, question_ids=[row.question_id], source_ids=row.supporting_source_ids))
    for conflict in response.conflicts:
        actions.append(ActionItem(rank=0, action=f"Compare scope, dates and values: {conflict.question}",
                                  reason=conflict.detail, priority="high", question_ids=[conflict.question_id],
                                  source_ids=[v.source_id for v in conflict.values]))
    for source in response.sources:
        if source.fetch_status != "ok":
            actions.append(ActionItem(rank=0, action=f"Retry or replace the inaccessible source: {source.url or source.title or source.id}",
                                      reason=source.error or "Source could not be read.", priority="medium", source_ids=[source.id]))
    # Trust-tier alert (Layer 3 Alert 1, lightweight form): if no
    # readable source is official, add a high-priority verify-next
    # action. It is appended (not inserted first) so the existing
    # priority order — unanswered questions first — is preserved.
    # Pasted texts have no host, so they count as unknown, never as
    # official. No new gap kind is invented; the alert is an action
    # plus a summary sentence (below).
    _readable = [s for s in response.sources if s.fetch_status == "ok" and s.text_length > 0]
    if _readable and not any(_source_tier(s.url) == "official" for s in _readable):
        actions.append(ActionItem(
            rank=0, action="Find an official source for this topic",
            reason="No official source was reviewed in this run. Findings from non-official sources should be verified against an official source before relying on them.",
            priority="high", question_ids=[], source_ids=[s.id for s in _readable]))
    actions.sort(key=lambda a: {"high": 0, "medium": 1, "low": 2}[a.priority])
    for i, action in enumerate(actions, 1):
        action.rank = i
    covered = sum(c.status == "covered" for c in response.coverage)
    partial = sum(c.status == "partial" for c in response.coverage)
    readable = sum(s.fetch_status == "ok" and s.text_length > 0 for s in response.sources)
    if readable == 0:
        # Regression guard (pre-2.0 behaviour): a generic "0 readable"
        # summary hides the actual failure. Say plainly that nothing
        # could be read and the inaccessible inputs must be fixed first.
        summary = ("No sources could be read, so no question could be answered from evidence. "
                   "Fix the inaccessible inputs first, then re-run the analysis.")
    else:
        summary = (f"Across {readable} readable source(s), {covered} of {len(response.coverage)} question(s) have strong keyword coverage, "
                   f"{partial} have partial coverage and {len(response.unanswered_questions)} have no matching evidence. "
                   f"{len(response.conflicts)} possible conflict(s) need verification. Coverage measures text overlap, not factual correctness.")
        if not any(_source_tier(s.url) == "official" for s in response.sources if s.fetch_status == "ok" and s.text_length > 0):
            summary += " No official source was reviewed in this run."
    return response.model_copy(update={"gaps": gaps, "actions": actions, "summary": summary})


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
    # Optional semantic expansion, one Groq call per run: a mapping
    # from an original word to its equivalent terms, used only to
    # select sentences. Any failure (no key, bad JSON, timeout)
    # yields {} and the static clusters carry the run. Stem both
    # sides so expanded terms meet sentence tokens on the same
    # footing; _score checks expanded[token] per token, so one
    # expanded term can never inflate unrelated tokens.
    try:
        _expanded_raw = derive_semantic_terms([q for _, q, _ in questions])
    except Exception:
        _expanded_raw = {}
    expanded_for_score: dict[str, set[str]] = {
        _stem(word): {_stem(t) for t in terms} for word, terms in _expanded_raw.items()
    }
    records: list[SourceRecord] = [c.record for c in collected]
    texts: dict[str, str] = {c.record.id: c.text for c in collected if c.text}
    # Identical sources are not independent corroboration. Flag exact
    # duplicates (whitespace/case-normalized) in notes, which the
    # frontend Overview renders; do not invent a new gap kind or
    # drop a source, and do not guess at near-duplicates.
    _by_text: dict[str, list[str]] = {}
    for _item in collected:
        if _item.record.fetch_status == "ok" and _item.text:
            _by_text.setdefault(_normalize_for_match(_item.text).lower(), []).append(_item.record.id)
    for _ids in _by_text.values():
        if len(_ids) >= 2:
            notes.append(
                f"{' and '.join(_ids)} contain identical text; "
                "treat them as one source, not independent corroboration."
            )
    accessible = [c for c in collected if c.record.fetch_status == "ok" and c.text]
    inaccessible_ids = [c.record.id for c in collected if c.record.fetch_status != "ok"]

    coverage: list[QuestionCoverage] = []
    conflicts: list[PossibleConflict] = []
    gaps: list[GapItem] = []
    sentences_cache: dict[str, list[str]] = {}
    tokens_cache: dict[str, set[str]] = {}
    for question_id, question, origin in questions:
        tokens = _tokens(question)
        passages = _best_passages(tokens, collected, sentences_cache, tokens_cache, expanded_for_score)
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

    response = AnalysisResponse(
        mode=mode,
        goal=goal,
        questions_analyzed=len(coverage),
        coverage_percent=0,
        summary="",
        disclaimer=disclaimer,
        sources=records,
        coverage=coverage,
        unanswered_questions=[],
        gaps=gaps,
        conflicts=conflicts,
        freshness_warnings=freshness_warnings,
        actions=[],
        inaccessible_source_ids=inaccessible_ids,
        analysis_method=method,
        notes=notes,
        analyzed_at=datetime.now(timezone.utc),
    )
    cleaned, validation_notes = _validate(response, texts)
    if validation_notes:
        cleaned = cleaned.model_copy(update={"notes": [*cleaned.notes, *validation_notes]})
    return cleaned
