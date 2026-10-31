# GapLens — Digital Dark Spot

**SHINCHAN Online Hackathon 2026 · Problem statement: Digital Dark Spot (team DEVENGERS, individual entry)**

GapLens compares sources on one topic and surfaces what is missing, what disagrees, what is outdated or undated,
and what to verify next — with evidence shown, and AI findings labelled as *potential signals*, never as facts.
A generic chatbot summary does not satisfy this problem statement, and neither does a fake one: this repo therefore
has **no fake search and no fake citations**.

> **Foundation build (v0.1.0-foundation).** This commit is the foundation only: clean structure, typed schemas,
> health endpoint, configurable CORS, backend-only secrets, an honestly labelled offline sample, and a one-URL fetch
> utility. The analysis engine, real database persistence, re-check/diff, and export are the next layers — they are
> listed under "Not in this foundation" below, not silently pretended to exist.

## What this foundation does

- **Health:** `GET /api/health` — service, version, environment, and `groq_configured` (boolean only).
- **Honest sample:** `GET /api/sample` — a bundled scholarship demo (86% coverage, one renewal gap, two possible
  conflicts, five-item verify-next checklist). Every source has `is_sample: true` and **no URL**, on purpose:
  a sample must never look like a citation.
- **One-URL fetch:** `POST /api/fetch` with `{"url": "..."}` — fetches exactly the public URL the user pastes
  (Requests + BeautifulSoup), returns title + opening text, and turns blocked/paywalled/failed pages into a clear
  message instead of a crash. No analysis is derived from it in this build.
- **Frontend:** React + Vite + TypeScript + Tailwind + Lucide. One page: backend health, the offline sample
  (coverage bar, slots, gaps, conflicts with both quotes side by side, checklist), and the fetch preview.

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
| `GROQ_MODEL` | backend only | *(unset)* | Model name, used only once the analysis layer is built. |
| `CORS_ORIGINS` | backend only | `http://localhost:5173` | Comma-separated. Change it when the frontend origin changes; do not use `*` in production. |
| `ENVIRONMENT` | backend only | `development` | Reported by `/api/health`. |
| `VITE_API_URL` | frontend only | `http://localhost:8000` | Backend base URL. The only frontend env var. |

## API

| Method | Path | Response |
|---|---|---|
| `GET` | `/` | Service + version |
| `GET` | `/api/health` | `HealthResponse` |
| `GET` | `/api/sample` | `SampleAnalysis` (`mode: "offline_sample"`) |
| `POST` | `/api/fetch` | `FetchResponse` (`ok` / `blocked` / `failed` / `unsupported`) |

Schemas: `backend/app/schemas.py`. The frontend mirrors them in `frontend/src/lib/types.ts` — change both together.

## Repo layout

```
gaplens (repo: digital-dark-spot)
├── frontend/            Vite + React + TS + Tailwind + Lucide
│   └── src/lib/         types.ts (mirrors backend schemas), api.ts (typed client)
├── backend/             FastAPI
│   ├── app/main.py      routes + CORS wiring only
│   ├── app/config.py    backend-only settings (secrets never leave the server)
│   ├── app/schemas.py   Pydantic v2 response/request types
│   ├── app/sample.py    labelled offline demo data
│   ├── app/fetcher.py   one-URL fetch (Requests + BeautifulSoup)
│   └── tests/test_api.py  honesty checks (no secret leak, sample labelled, fetch guard)
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

## Not in this foundation (next layers)

Live multi-source analysis engine (coverage matrix, conflict + freshness engines, evidence drawer), real database
persistence (the earlier Next.js prototype used Supabase; this rewrite has no DB yet), re-check + diff, trust tiers,
templates beyond the one demo, and PDF/text export. None of these is claimed anywhere in the UI.

## Limitations to know

- The fetch hostname guard blocks literal private/local addresses; it is a basic check, not a full SSRF proof.
  Do not expose the backend publicly without a proper SSRF guard and rate limiting.
- CORS defaults allow only the local Vite origin. Production origins must be set explicitly via `CORS_ORIGINS`.
- The Groq model name is intentionally unset by default: pin a real free-tier model when the analysis layer lands,
  and verify it against Groq's current model list rather than trusting this file.

## Starter templates

The 11 DigiDoor starter templates (10 repos + the gstack process layer) are applied in
[`docs/digidoor-starter-checklist.md`](docs/digidoor-starter-checklist.md) — each one listed as applied, limited,
or deliberately skipped, with the reason. Nothing is silently dropped.
