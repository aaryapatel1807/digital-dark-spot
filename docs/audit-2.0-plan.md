# GapLens 2.0 — Audit (latest) + implementation plan

## Latest implementation (verified 1 Nov, remote main c953194)

- Frontend: React 18 + Vite 5 + TS + Tailwind, routes `/` landing
  (hero input + examples), `/dashboard` (home, new-research,
  my-research, gaps, conflicts, graph, freshness, checklist,
  sources, reports, settings). Reports default to Simple view,
  Research view keeps the full dashboard. Reports live in browser
  localStorage only; no database, no sync.
- Backend: FastAPI + Pydantic v2, endpoints `GET /`, `/api/health`
  (boolean-only `groq_configured`), `/api/sample`, `POST /api/fetch`,
  `POST /api/analyze` (live + labelled demo). 70 tests passing.
- Engine: deterministic token-overlap (0.50/0.25, ≥2 matched terms),
  synonym pairs (incl. renew/continue family, verified live),
  numeric (money/percent/year/date/bare-number) + stance possible
  conflicts with both quotes, freshness (stale >365d, undated never
  guessed), trust-tier alert, gaps, ranked actions, final quote
  validation sweep (quote must be a verbatim substring).
- AI: Groq only proposes questions from the goal only; source text
  never leaves the server; no LLM output becomes a finding.
- Fetching: SSRF-safe (blocked hosts, DNS IP checks, redirect
  re-validation, 10 s, 1 MB, 5 workers, per-source failure
  isolation). Rate limits per-process: fetch 60/min, analyze 30/min.
- Live: Vercel frontend gaplens-omega.vercel.app + SnapDeploy
  backend gaplens-backend-77c25 (Free Small, sleeps 15 min idle).
  WARNING (1 Nov ~10:40 IST): SnapDeploy free deploys were used up
  for the 12-hour window — backend pushes may not auto-deploy live
  until that window resets. Frontend (Vercel) deploys are separate.

## Plan, in dependency order (each step tested + pushed before next)

1. **Semantic intelligence (Step 2):** concept clusters (not just
   pairs) + improved stemming + phrase matches ("open to" for
   eligibility, "last date" for deadline) + optional Groq term
   expansion (one call per run, goal/questions only, validated
   single-word terms, any failure → static clusters). Expanded
   terms only SELECT sentences; quotes are still verified verbatim.
   This is paraphrase-aware matching, not embeddings — no local
   model fits the 512 MB free container, and no new paid API is
   added. Labelled honestly in code and docs.
2. **Source discovery (Step 3):** `POST /api/discover` via SerpApi
   (Google engine) ONLY when `SERPAPI_KEY` is set server-side
   (user adds it in the SnapDeploy dashboard, as with Groq).
   Without a key the endpoint returns 503 "search not configured"
   and the UI says so — never invented URLs. Discovered results
   are suggestions only; they become analyzed sources only after
   the user selects them and the existing SSRF fetcher reads them.
3. **Document intelligence (Step 4):** `POST /api/pdf-text`
   (pypdf, ≤5 MB, ≤50 pages, ≤200,000 chars) returning per-page
   text. Frontend inserts the text as a pasted source with
   `[Page N]` markers, so page references survive into evidence
   quotes through the existing pipeline. No other formats claimed.
4. **Ask GapLens (Step 5):** `POST /api/ask` — deterministic
   retrieval over the report's own evidence (coverage quotes,
   gaps, conflicts, actions). No LLM writes the answer, so no
   hallucinated citation is possible: matched evidence is quoted
   with source IDs, otherwise it says it cannot answer from this
   evidence and points at the verify-next list. Citation IDs are
   validated against the submitted report.
5. **Evidence graph (Step 6):** extend the existing graph (it
   already links question → passage → source, plus gap/conflict
   nodes) with gap explanations, conflict side-by-side quotes in
   the detail pane, and clickable passage/source nodes (already
   wired to the source drawer) — no new decorative visualization.
6. **Tests + live verification (Step 7):** new tests for paraphrase
   clusters, Groq-expansion failure fallback, different-year
   conflicts (flagged possible, with the caveat already in the UI),
   discovery failure/no-key, PDF extraction + oversize/invalid
   rejection, fabricated Ask citations, and Ask grounding. Full
   backend suite + frontend build before each push; live check
   after SnapDeploy deploy window resets.

## Deliberately NOT claimed

Embeddings, internet search without a configured provider, PDF
formats beyond text-based PDF, an LLM assistant that "knows"
answers beyond the report, backend persistence, or any live
deployment that has not been verified after the deploy-window reset.
