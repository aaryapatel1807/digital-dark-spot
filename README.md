# GapLens — Digital Dark Spot

**SHINCHAN Online Hackathon 2026 · Problem statement: Digital Dark Spot (team DEVENGERS, individual entry)**

GapLens compares sources on one topic and surfaces what is missing, what disagrees, what is outdated or undated,
and what to verify next — with evidence shown, and AI findings labelled as *potential signals*, never as facts.
A generic chatbot summary does not satisfy this problem statement, and neither does a fake one: this repo therefore
has **no fake search and no fake citations**.

> **Analysis build (v0.2.0-analysis).** The foundation's sample and one-URL fetch remain, and the analysis
> engine has now landed: `POST /api/analyze` takes a research goal, public URLs, and pasted text, and returns
> a strict Pydantic result — summary, per-question coverage, unanswered questions, possible conflicts with
> both quotes, freshness warnings, and a prioritized verify-next action list. Every quote is validated
> server-side against the collected text before the response leaves. The frontend is untouched by this
> layer: it keeps calling health, sample, and fetch exactly as before, and can adopt `/api/analyze` later
> without any backend change.

## What this build does

- **Health:** `GET /api/health` — service, version, environment, and `groq_configured` (boolean only).
- **Honest sample:** `GET /api/sample` — a bundled scholarship demo (86% coverage, one renewal gap, two possible
  conflicts, five-item verify-next checklist). Every source has `is_sample: true` and **no URL**, on purpose:
  a sample must never look like a citation.
- **One-URL fetch:** `POST /api/fetch` with `{"url": "..."}` — fetches exactly the public URL the user pastes
  (Requests + BeautifulSoup), returns title + opening text, and turns blocked/paywalled/failed pages into a clear
  message instead of a crash. No analysis is derived from it in this build.
- **Frontend:** React + Vite + TypeScript + Tailwind + Lucide. One page: backend health, the offline sample
  (coverage bar, slots, gaps, conflicts with both quotes side by side, checklist), and the fetch preview.
  It does not yet call `/api/analyze`; that wiring is a frontend task, not a backend redesign.
- **Analysis:** `POST /api/analyze` — goal + URLs + pasted text in, strict result out (summary, coverage,
  unanswered questions, possible conflicts with both quotes, freshness warnings, prioritized actions).
  `mode: "offline_sample"` returns the bundled demo through the same engine, clearly labelled.

## Analysis: `POST /api/analyze`

Request (`AnalyzeRequest`, unknown fields rejected):

```json
{
  "goal": "Scholarship application",
  "questions": ["Who is eligible?", "What renews the scholarship next year?"],
  "urls": ["https://example.com/scholarship"],
  "texts": [{"title": "Pasted guide", "text": "..."}],
  "mode": "live"
}
```

- `goal` is required for live runs (3–2000 chars). `questions` are optional: when omitted, Groq proposes
  them if a key is configured, otherwise template questions derived from the goal are used.
- `mode: "offline_sample"` skips all fetching and returns the bundled demo through the same engine, labelled
  `mode: "offline_sample"` with `is_sample: true` sources and no URLs. A request goal is ignored in sample
  mode so the demo can never look like a live result about something else.
- Limits, enforced by the schema and the fetcher: at most 20 inputs (URLs + pasted texts), 20 questions,
  200,000 chars per pasted text, 10 s per fetch, 1 MB per page, 3 redirects.

Response (`AnalysisResponse`):

- `summary` — counts only: accessible/inaccessible sources, covered/partial/unanswered questions, conflicts,
  stale/undated sources. No claim is made that the data does not support.
- `sources` — one record per input, in order (`S1`, `S2`, …). Inaccessible URLs keep their record with an
  explicit `fetch_status` and error. `fetch_status` distinguishes **`not_found`** (HTTP 404/410: the host
  exists, the page does not) from **`nonexistent`** (DNS failure: the host does not resolve), plus `blocked`
  (safety refusal or 401/403/429), `timeout`, `too_large`, `unsupported`, `failed`.
- `coverage` — per question: `covered` / `partial` / `not_found`, supporting source IDs, and up to 5
  evidence quotes. Coverage is deterministic token-overlap scoring (thresholds 0.50 / 0.25, partial needs
  ≥ 2 matched terms, tight synonym pairs) — precision over recall, so a single shared topic word never
  counts as partial coverage.
- `conflicts` — `possible conflict` only, never adjudicated: numeric (different money/percent/year/date
  values for the same question across sources) or stance (one passage denies a term another affirms),
  always with both quotes.
- `freshness_warnings` — sources older than 365 days (`stale`, with age in days) and sources with no
  publication date (`undated`, `published_date: null`). Undated is never guessed.
- `gaps` — unanswered, partial, single-source-only, stale-only, undated-only.
- `actions` — ranked verify-next list: unanswered questions and conflicts first (high), then partial,
  corroboration, and retry/replace for each inaccessible source.
- Validation is structural: before responding, the engine re-checks that every referenced source ID
  exists and every quote is a substring of its source's collected text. Anything failing is dropped and
  noted in `notes`, never shipped. Groq, when configured, only ever proposes *questions* — it never
  writes findings, summaries, or quotes, so a model hallucination cannot become evidence.

## Stack

| Layer | Choice |
|---|---|
| Frontend | React 18 + Vite 5 + TypeScript (strict) + Tailwind CSS 3 + Lucide icons |
| Backend | Python 3.12 + FastAPI + Pydantic v2 |
| Fetching | Requests + BeautifulSoup (user-supplied public URLs only) |
| AI (optional) | Groq API, **only if a free key is configured** in the backend env; absent key = sample mode |

## Quickstart

```bash
# Backend (from repo root)
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cp .env.example .env        # optional; leave GROQ_API_KEY blank for sample mode
.venv/bin/uvicorn app.main:app --reload --port 8000   # http://localhost:8000/docs

# Frontend (new terminal, from repo root)
cd frontend
npm install
cp .env.example .env        # VITE_API_URL=http://localhost:8000
npm run dev                 # http://localhost:5173
npm run build               # production build check
```

Backend checks: `cd backend && .venv/bin/python -m pytest tests/ -q`

## Configuration

| Variable | Where | Default | Notes |
|---|---|---|---|
| `GROQ_API_KEY` | backend only | *(unset)* | Free Groq key. Unset = sample mode. Never in frontend code, never in a response. |
| `GROQ_MODEL` | backend only | *(unset)* | Model name, used only to propose questions when no questions are supplied; defaults to `llama-3.1-8b-instant`. |
| `CORS_ORIGINS` | backend only | `http://localhost:5173` | Comma-separated. Change it when the frontend origin changes; do not use `*` in production. |
| `ENVIRONMENT` | backend only | `development` | Reported by `/api/health`. |
| `VITE_API_URL` | frontend only | `http://localhost:8000` | Backend base URL. The only frontend env var. |

## API

| Method | Path | Response |
|---|---|---|
| `GET` | `/` | Service + version |
| `GET` | `/api/health` | `HealthResponse` |
| `GET` | `/api/sample` | `SampleAnalysis` (`mode: "offline_sample"`) |
| `POST` | `/api/fetch` | `FetchResponse` (`ok` / `blocked` / `failed` / `unsupported` / `not_found` / `nonexistent` / `timeout` / `too_large`) |
| `POST` | `/api/analyze` | `AnalysisResponse` (see "Analysis" above; `mode: "offline_sample"` for the labelled demo) |

Schemas: `backend/app/schemas.py` (foundation shapes) and `backend/app/analysis_schemas.py` (analysis shapes).
The frontend mirrors the foundation schemas in `frontend/src/lib/types.ts` — change both together. Note: the
frontend's `FetchStatus` union predates the new `not_found` / `nonexistent` / `timeout` / `too_large` values;
they are additive display strings, but the union wants syncing when the frontend adopts `/api/analyze`.

## Repo layout

```
gaplens (repo: digital-dark-spot)
├── frontend/            Vite + React + TS + Tailwind + Lucide (unchanged by this layer)
│   └── src/lib/         types.ts (mirrors backend schemas), api.ts (typed client)
├── backend/             FastAPI
│   ├── app/main.py      routes + CORS wiring only
│   ├── app/config.py    backend-only settings (secrets never leave the server)
│   ├── app/schemas.py   Pydantic v2 foundation types
│   ├── app/analysis_schemas.py  strict /api/analyze request + response types
│   ├── app/fetcher.py   SSRF-safe one-URL fetch (Requests + BeautifulSoup)
│   ├── app/collector.py source IDs + per-run collection (URLs + pasted text)
│   ├── app/analyzer.py  deterministic coverage / conflict / freshness / gaps engine + validation sweep
│   ├── app/groq_client.py  optional question proposals only (goal in, questions out)
│   ├── app/sample.py    foundation labelled offline demo data
│   ├── app/sample_analysis.py  /api/analyze offline_sample demo through the same engine
│   └── tests/           fetcher SSRF + mapping, analyzer honesty, endpoint shape tests
└── docs/
    ├── digidoor-starter-checklist.md   the 11 starter templates, applied or skipped with reasons
    └── architecture.html               single-file HTML+SVG architecture diagram
```

## Honesty rules (standing)

1. No search endpoint until search is real. No citations are generated; a source is cited only when its text was
   actually fetched, with the exact quote attached.
2. Findings say "potential gap" / "possible conflict". The product never picks a winner between conflicting sources.
3. Sample data is labelled `offline_sample` / `is_sample` in the API, the UI banner, and this README.
4. A failed fetch is a result with a message, never a crash and never invented content.

## Not in this build (next layers)

Real database persistence (the earlier Next.js prototype used Supabase; this rewrite has no DB yet),
re-check + diff, trust tiers, templates beyond the one demo, and PDF/text export. None of these is claimed
anywhere in the UI. The analysis engine itself is done: coverage, conflict, freshness, gaps, and actions
are live in `POST /api/analyze`.

## Limitations to know

- The SSRF guard blocks RFC1918/loopback/link-local/CGNAT/ULA/multicast/unspecified addresses and
  re-validates every redirect hop, but DNS can change between validation and connection (TOCTOU /
  rebinding). The check runs immediately before each request, which closes the casual hole; do not expose
  the backend publicly without rate limiting in front of it.
- Coverage is keyword-overlap scoring, not language understanding: it favours precision (no fabricated
  coverage) over recall, so a well-answered question phrased very differently from its sources can read
  as `not_found`. Every quote is still verbatim, so a human can judge in seconds.
- Pages that need JavaScript to render are not executed — only served HTML/text is extracted.
- CORS defaults allow only the local Vite origin. Production origins must be set explicitly via `CORS_ORIGINS`.
- The Groq model defaults to `llama-3.1-8b-instant` when `GROQ_MODEL` is unset; verify it against Groq's
  current model list rather than trusting this file, and note Groq is only ever used to propose questions.

## Starter templates

The 11 DigiDoor starter templates (10 repos + the gstack process layer) are applied in
[`docs/digidoor-starter-checklist.md`](docs/digidoor-starter-checklist.md) — each one listed as applied, limited,
or deliberately skipped, with the reason. Nothing is silently dropped.
