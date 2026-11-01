# GapLens 3.0 — Architecture map & baseline evaluation (1 Nov 2026)

## Baseline (verified, remote main cf0fcd1 before 3.0 work)

- 99 backend tests passing; frontend build green.
- Pipeline (existing, preserved): goal → questions (user / Groq /
  templates) → collect (SSRF-safe fetch, pasted text, PDF) →
  deterministic overlap scoring (0.50 covered / 0.25 partial, ≥2
  matched) + concept clusters + phrase matches + optional Groq term
  expansion → numeric/stance possible conflicts → temporal
  classification → freshness → gaps/actions → validation sweep
  (quote must be a verbatim substring) → dashboard.
- Live: Vercel frontend (latest verified frontend lags the newest
  commit — see final-stabilization doc), SnapDeploy backend still
  pre-2.0 until its free-deploy window resets. Nothing in 3.0 claims
  a live deployment that has not been verified.

## Data flow (3.0, additive only)

```
goal → questions → collected sources (text, per source)
  → sentences + tokens (cache) → _best_passages (deterministic)
  → coverage status (unchanged thresholds)
  → TF-IDF cosine over concept-expanded tokens (IDF from this run's
    corpus) → semantic_score + entailment label per question
  → scope-narrowing downgrade (universal question + restricted
    evidence: covered → partial)
  → suggested questions (domain taxonomy, deduplicated by Jaccard
    ≥0.5, re-checked against the same evidence) — suggestions only
  → conflicts (unchanged) → structured claims (numbers, period,
    conditions, scope, negation from the quotes only) →
    contextual_conflicts (direct / temporal / conditional / scope /
    partial / insufficient_context)
  → evidence provenance (text_offset, PDF page from [Page N])
  → validation sweep (unchanged, now preserves entailment, semantic
    score, classification) → gaps/actions (unchanged)
  → AnalysisResponse (+ suggested_questions, contextual_conflicts,
    semantic_analysis, analysis_limitations) → Simple/Research views
    (same result, both views)
```

## Why no neural embeddings (documented decision)

A sentence transformer was evaluated and rejected for this
deployment: 512 MB free container, ~80 MB model download plus
runtime memory risking OOM and cold-start timeouts, no paid
embedding API allowed, and no HF token configured. "Hybrid" here
means deterministic overlap + concept expansion + TF-IDF cosine.
If an embedding model is ever configured, `semantic_analysis.model`
must name it and scores must be re-labelled as that model's
similarity — never as a probability of truth. The deterministic
engine remains the fallback and the coverage authority; TF-IDF
never marks a question covered on its own.

## Evaluation (backend/tests/test_intelligence_3.py)

Labelled fixtures, thresholds asserted in the suite:
- Paraphrase retrieval (continuation-as-extension, open-to
  eligibility, last-date deadline): 3/3 retrieved (covered or
  partial — conditional continuation is honestly partial).
- False-covered for insufficient evidence (broad "all students"
  vs narrow disadvantaged-group evidence; unrelated scheme text):
  0 false-covered. The broad-vs-narrow case is caught by the
  scope-narrowing downgrade.
- Negation: "not eligible" passage → entailment `negated_answer`,
  not support.
- Temporal: 2024 vs 2026 → `temporal_difference`, periods preserved.
- Partial: shared + differing numbers → `partial_disagreement`.
- Provenance: PDF page marker → page 3 + offset preserved.
- Prompt injection: source text containing instructions produces
  no injected finding (source text is data, never instructions;
  Groq receives goal/questions only).
- Baseline comparison, stated honestly: the deterministic engine
  alone already retrieved the same 3 paraphrase cases via clusters
  and phrases; TF-IDF adds a retrieval score and the
  related-but-insufficient label, it does not change coverage
  thresholds. No claim of a measured accuracy gain over baseline
  is made, because the evaluation set is small (5 cases) and the
  TF-IDF layer is a ranking/labeling aid, not a new coverage rule.

## Resource findings

- No new dependencies, no model downloads, no per-request external
  calls beyond existing Groq (optional) and SerpApi (optional).
- Corpus is bounded by the existing 20-input / 200,000-char caps;
  TF-IDF is computed over cached sentence token sets in-process.
- Backend startup unchanged (no model load).

## Remaining limitations

- Semantic retrieval is lexical-conceptual, not neural: paraphrases
  with no shared concept, synonym, or phrase still miss.
- TF-IDF semantic_score can be 0.0 while deterministic coverage
  succeeds via a phrase match (phrase matches are not in the TF-IDF
  vector) — the score is supplementary, never the coverage rule.
- Suggested questions come from a fixed domain taxonomy, not from
  source topics; Groq question generation (when a key is set) is
  separate and only applies when the user supplies no questions.
- Structured claims extract numbers/periods/conditions from quotes
  by pattern, not by parsing: unknown fields stay unknown, and a
  claim's subject is the question text, not a parsed entity.
- Live 3.0 backend is not deployed (SnapDeploy window); live
  frontend lags the newest commit (verified 12:04 IST).
