# GapLens — Digital Dark Spot

**SHINCHAN Online Hackathon 2026 · Problem statement: Digital Dark Spot (team DEVENGERS, individual entry)**

GapLens compares sources on one topic and surfaces what is missing, what disagrees, what is outdated or undated,
and what to verify next — with evidence shown, and AI findings labelled as *potential signals*, never as facts.
A generic chatbot summary does not satisfy this problem statement, and neither does a fake one: this repo therefore
has **no fake search and no fake citations**.

> **Live (1 Nov 2026).** Frontend: https://gaplens-omega.vercel.app (Vercel).
> Backend: https://gaplens-backend-77c25.containers.snapdeploy.app (SnapDeploy, free tier —
> sleeps after 15 minutes idle, wake it via `/api/health` before demoing; it takes 60–90
> seconds to wake). Backend version 2.0.0, environment production, verified live:
> frontend header "Backend connected", live (non-demo) reports run end to end.
>
> **GapLens 2.0 (in repo, backend deploy pending SnapDeploy free-deploy
> window reset — see Deployment):** semantic paraphrase matching
> (concept clusters + phrase matches + optional Groq term expansion,
> NOT embeddings), source discovery via SerpApi only when
> `SERPAPI_KEY` is set server-side (otherwise 503, never invented
> URLs), PDF text extraction (≤5 MB, ≤50 pages, page markers in
> evidence), deterministic Ask GapLens over report evidence only,
> and richer evidence-graph detail panes. See
> `docs/audit-2.0-plan.md` for the audit and honest scope.
>
> **Analysis build (v2.0.0).** `POST /api/analyze` takes a research goal, public URLs, and pasted text, and returns
> a strict Pydantic result — summary, per-question coverage, unanswered questions, possible conflicts with
> both quotes, freshness warnings, trust-tier alert, and a prioritized verify-next action list. Every quote is validated
> server-side against the collected text before the response leaves. See
> [`docs/submission.md`](docs/submission.md) for the submission pack and demo script.

## What this build does

- **Health:** `GET /api/health` — service, version, environment, and `groq_configured` (boolean only).
- **Honest sample:** `GET /api/sample` — a bundled scholarship demo (86% coverage, one renewal gap, two possible
  conflicts, five-item verify-next checklist). Every source has `is_sample: true` and **no URL**, on purpose:
  a sample must never look like a citation.
- **One-URL fetch:** `POST /api/fetch` with `{"url": "..."}` — fetches exactly the public URL the user pastes
  (Requests + BeautifulSoup), returns title + opening text, and turns blocked/paywalled/failed pages into a clear
  message instead of a crash. No analysis is derived from it in this build.
- **Frontend:** React + Vite + TypeScript + Tailwind + Lucide — a research intelligence dashboard (warm
  paper, deep ink, restrained indigo): research brief input (goal, questions, URLs, pasted text), Live /
  Demo mode switch, overview, interactive evidence coverage matrix, side-by-side conflict explorer, source
  drawer with links and passages, freshness/uncertainty warnings, and a prioritized verify-next checklist
  with local ticks and copy. Loading, error + retry, and empty-goal validation states included; nothing is
  rendered that the backend did not return. The old foundation page (health card, sample view, fetch
  preview) was replaced by the dashboard; the backend endpoints it used are unchanged.
- **Analysis:** `POST /api/analyze` — goal + URLs + pasted text in, strict result out (summary, coverage,
  unanswered questions, possible conflicts with both quotes, freshness warnings, trust-tier alert,
  prioritized actions).
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
- `coverage` — per question: `covered` / `partial` / `not_found`, supporting source IDs, and
  evidence quotes for every supporting source. Coverage is deterministic token-overlap scoring (thresholds 0.50 / 0.25, partial needs
  ≥ 2 matched terms, tight synonym pairs) — precision over recall, so a single shared topic word never
  counts as partial coverage.
- `trust` — source tiers from URL host only (government = official, academic = university, small
  known-news list = news, everything else including pasted text = unknown). If no readable source
  is official, the summary says so and a high-priority verify-next action asks for an official source.
- `conflicts` — `possible conflict` only, never adjudicated: numeric (different money/percent/year/date/
  bare-number values for the same question across sources — bare numbers cover scores and counts such
  as CGPA 7.0 vs 7.5) or stance (one passage denies a term another affirms),
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
| `CORS_ORIGINS` | backend only | `http://localhost:5173,http://localhost:4173` | Comma-separated exact origins (scheme + host, no path, no trailing slash). Change it when the frontend origin changes; do not use `*` in production. |
| `ENVIRONMENT` | backend only | `development` | Reported by `/api/health`. Set to `production` on SnapDeploy. |
| `VITE_API_URL` | frontend only | `http://localhost:8000` | Backend base URL (origin only, no `/api` suffix, no trailing slash). The only frontend env var. Dev reads `frontend/.env.development`; production builds read the hosting dashboard's env var (see Deployment below) — Vite bakes it in at build time. |

## API

| Method | Path | Response |
|---|---|---|
| `GET` | `/` | Service + version |
| `GET` | `/api/health` | `HealthResponse` |
| `GET` | `/api/sample` | `SampleAnalysis` (`mode: "offline_sample"`) |
| `POST` | `/api/fetch` | `FetchResponse` (`ok` / `blocked` / `failed` / `unsupported` / `not_found` / `nonexistent` / `timeout` / `too_large`) |
| `POST` | `/api/analyze` | `AnalysisResponse` (see "Analysis" above; `mode: "offline_sample"` for the labelled demo) |
| `POST` | `/api/discover` | `DiscoverResponse` (SerpApi suggestions only; 503 when `SERPAPI_KEY` is unset) |
| `POST` | `/api/pdf-text` | `PdfTextResponse` (per-page text, `[Page N]` markers; 415 non-PDF, 422 oversize/textless) |
| `POST` | `/api/ask` | `AskResponse` (deterministic answer from the submitted report's evidence only) |

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

Real database persistence (the earlier Next.js prototype used Supabase; this rewrite has no DB yet —
reports live in the browser in this build), re-check + diff, full trust-tier UI (tiers can be
overridden in the UI), templates beyond the one demo, and PDF/text export. None of these is claimed
anywhere in the UI. The analysis engine itself is done: coverage, conflict, freshness, gaps, trust
alert, and actions are live in `POST /api/analyze`.

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

## Deployment (free hosting, ₹0)

**Status: LIVE (verified 1 Nov 2026).**

| Part | Host | Live URL |
|---|---|---|
| Frontend (static Vite build) | Vercel, Hobby plan | https://gaplens-omega.vercel.app |
| Backend (FastAPI, `uvicorn app.main:app --host 0.0.0.0 --port 8000`, root directory `backend/`) | SnapDeploy, Free Small (512 MB / 0.25 vCPU) | https://gaplens-backend-77c25.containers.snapdeploy.app |

Both hosts auto-deploy from GitHub `main` (frontend redeploy on commit, backend
auto-deploy on push). The Vercel project is `gaplens`; the frontend build sets
`VITE_API_URL` to the SnapDeploy backend origin (origin only, no `/api` suffix).

### Free-tier facts and caveats (checked 31 Oct – 1 Nov 2026)

- **SnapDeploy Free Small:** the container **sleeps after 15 minutes without traffic
  and takes 60–90 seconds to wake** — the first visitor after a quiet spell sees a
  "Waking up" page, then the app works. **Wake the backend before you demo or present:**
  open `<backend>/api/health` first and wait for `{"status":"ok"}`.
- **Vercel Hobby:** $0 for personal, non-commercial projects, with CDN, HTTPS, and Git
  auto-deploy. A hackathon demo entry is a personal project, so Hobby fits.
- **Rate limiting** is per-process in this codebase. On a single container that
  behaves as documented; it would not hold across multiple instances or serverless replicas.
- **Preview deployments are NOT CORS-covered:** `CORS_ORIGINS` is an exact-origin list, so a
  Vercel preview URL (`*.vercel.app` with a different subdomain) will be blocked until you add
  it. Only the production frontend origin is configured: `https://gaplens-omega.vercel.app`.

### Environment variables (secure handling)

- **Backend secrets live only in the SnapDeploy dashboard** (Environment): `GROQ_API_KEY`
  (optional — leave unset and the API runs in honest demo mode), `GROQ_MODEL`,
  `CORS_ORIGINS`, `ENVIRONMENT`. They are never committed, never in frontend code, and
  never in a response — `/api/health` reports only `groq_configured: true/false`.
- **Frontend has exactly one env var, and it is not a secret:** `VITE_API_URL`, the backend
  origin. It is baked into the bundle at build time by Vite, so changing it requires a
  frontend redeploy. If a production build is ever made without it, the app logs a console
  warning saying so instead of failing silently.
- **Local development is unchanged:** `npm run dev` reads `frontend/.env.development`
  (`http://localhost:8000`), which production builds never read.

### Verified live pair (1 Nov 2026)

- Backend `/api/health` returns `{"status":"ok","version":"2.0.0","environment":"production",
  "groq_configured":true}`.
- Frontend header says **Backend connected**, not "Backend unreachable".
- Live analysis (goal + pasted texts) runs end to end, including the CGPA 7.0 vs 7.5
  bare-number conflict (see `docs/submission.md` for the demo script).
- Demo mode banner still says "Demo data — not a live result".

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Frontend says "Backend unreachable" | `VITE_API_URL` missing, wrong, or has a trailing `/api` | Fix the Vercel env var (origin only) and **redeploy** — env vars are build-time |
| Browser console: CORS error on `/api/analyze` | `CORS_ORIGINS` does not exactly match the frontend origin | Fix the SnapDeploy env var to the exact production URL, wait for restart |
| SnapDeploy shows a "Waking up" page, then works | Free container was asleep | Expected (60–90 second wake). Warm it via `/api/health` before demos |
| Backend `/api/health` 404 or never starts | Wrong root directory or start command | Check SnapDeploy logs; root must be `backend/`, start must be the `uvicorn` command above |
| Groq errors in logs, questions still work | Bad or expired key | The engine falls back to template questions; fix or remove the key in the SnapDeploy dashboard |
| Vercel preview deployment cannot reach the API | Preview origins are not in `CORS_ORIGINS` | Add the preview origin temporarily, or test previews against demo mode only |

### Rollback

Redeploy the previous deployment in the Vercel dashboard (Deployments > ⋯ > Redeploy) and,
on SnapDeploy, redeploy an earlier commit. Suspending both services removes the
demo entirely; nothing in this app stores user data, so there is nothing to migrate back.

### Alternatives considered (not implemented)

- **Render (abandoned, do not retry without his word):** Blueprint sync failed, and the
  account's free instance limit was exhausted — manual creation was blocked at Deploy.
- **Railway (abandoned):** trial expired; free plan blocked new projects.
- **Backend on Vercel serverless:** possible, but it would need an `api/` serverless entry,
  and Hobby function timeouts could cut long multi-source analyses short. SnapDeploy keeps
  the existing process untouched.
- **Cloudflare Pages for the frontend:** also free and viable, but Vercel is already the
  account's established frontend host, so no new account is needed for the demo.
