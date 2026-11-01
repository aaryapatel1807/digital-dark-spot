# GapLens — Final production stabilization & free-tier optimization (1 Nov 2026)

## Part 1 — Verified status matrix (remote main, 1 Nov 2026)

| Feature | Code | Tested | Deployed live | Notes |
|---|---|---|---|---|
| Research question entry, templates, manual URLs, pasted text | Yes | Yes (suite) | Yes (pre-2.0 backend) | Core, never needs SerpApi |
| PDF text extraction (5 MB / 50 pp, page markers) | Yes | Yes | No — backend pre-2.0 | Frontend shows plain "needs 2.0 backend" on 404 |
| Semantic concept matching + phrase matches + Groq terms | Yes | Yes | No — backend pre-2.0 | Paraphrase-aware, NOT embeddings |
| Contradiction detection + temporal classification | Yes | Yes | No — backend pre-2.0 | same/different_period/conditions/scope/uncertain |
| Freshness warnings, citations, checklist, Simple/Research views | Yes | Yes | Yes (pre-2.0 backend) | Verified live in earlier checks |
| Ask GapLens (deterministic, report evidence only) | Yes | Yes | No — backend pre-2.0 | Frontend shows plain "needs 2.0 backend" on 404 |
| Interactive evidence graph + ErrorBoundary | Yes | Yes | Frontend live (verified 11:20 IST) | Graph scrolls inside its canvas on mobile; no page overflow |
| SerpApi discovery (provider interface, quotas, cache) | Yes | Yes | No — backend pre-2.0, and no SERPAPI_KEY set | Optional; see below |

**Broken / incomplete:** none in the tested suite. **Blocked by external
configuration:** (1) SnapDeploy free deploys used up for the 12-hour
window (resets ~22:30 IST 1 Nov) — backend pushes since `c953194`
have not auto-deployed live; (2) no `SERPAPI_KEY` set on SnapDeploy,
so discovery is unavailable live even after the backend deploys,
until the user adds it (optional, see below).

## Parts 2–4 — SerpApi is optional, not mandatory

- Modes: A manual URLs (SSRF-safe fetch, existing), B pasted text +
  PDF (existing), C automatic discovery (optional, provider interface
  in `backend/app/search_providers.py`: `SearchProvider.search()`).
- Only SerpApi is implemented; no engine is scraped, no provider was
  added merely for claiming to be free.
- Env (all server-side, never in frontend bundles):
  `SEARCH_PROVIDER=serpapi|none` (default serpapi),
  `DISCOVERY_ENABLED=true|false` (default true),
  `SERPAPI_KEY` (optional), `DISCOVERY_DAILY_GLOBAL_LIMIT=30`,
  `DISCOVERY_SESSION_LIMIT=3` (per IP per day — an abuse bucket, NOT
  authentication; shared networks share it),
  `DISCOVERY_RESULTS_LIMIT=5`, `DISCOVERY_CACHE_TTL_SECONDS=86400`,
  `DISCOVERY_QUOTA_PATH` (override for tests / custom data dir).
- Quota + cache live in `backend/app/discovery_quota.py` as a JSON
  file (`backend/data/discovery_quota.json`, created on first use):
  cache hits consume no quota, provider failures consume no quota,
  quota exhaustion returns a friendly 503 with no retry, provider
  429/quota errors are detected and not retried, identical
  concurrent queries serialize on a per-query lock and the second
  caller hits the cache. Frontend disables the Search button while
  loading (no double-click calls).
- Limitation, stated plainly: the JSON store is per-process best
  effort, not cross-worker atomic, and if the data dir is unwritable
  it falls back to in-memory counters for the process lifetime.
  Limits are therefore kept low. A real database would be needed
  for strict multi-worker accounting — not added, to stay ₹0 and
  free-tier.

## Part 5 — Source collection UX

New research now labels the three modes explicitly: Add Website Links
(Step 3), Upload Documents, Find Sources Automatically. Discovery
cards show Suggested source badge, title, domain, URL, snippet, and
cached/fresh retrieval metadata; selected sources move to Step 3 as
website links and only become analyzed evidence after a successful
fetch (failed fetches are shown as failed sources in the report).

## Parts 6–8 — Frontend stabilization & deployment

- Homepage: blank did NOT reproduce in live desktop checks (initial
  load, hard refresh, dashboard-and-back, all rendered). No console
  or network panel was available in the browser tool, so no console
  message is quoted. ErrorBoundary (added earlier) remains as the
  fallback for any future render crash. Homepage renders without the
  backend (backend-offline indicator is shown, navigation stays usable).
- Capabilities: `GET /api/capabilities` reports version + which
  optional features are available; the frontend falls back to the
  health boolean on an old backend (404) and never blocks on it.
- Deployment (exact steps, NOT claimed done): the code is pushed to
  GitHub main. When SnapDeploy's free-deploy window resets:
  1. SnapDeploy auto-deploys from main (Root Directory `backend`,
     start `uvicorn app.main:app --host 0.0.0.0 --port 8000`, port 8000).
  2. Keep existing env (`ENVIRONMENT=production`,
     `CORS_ORIGINS=https://gaplens-omega.vercel.app`, `GROQ_API_KEY`,
     `GROQ_MODEL`); optionally add `SERPAPI_KEY` + discovery limits.
  3. Wake via `/api/health`, then verify `/api/capabilities`
     (discovery_available should match your key choice),
     `/api/discover` (503 without a key, results with one),
     `/api/pdf-text`, `/api/ask`, and a live `/api/analyze` run.
  4. Vercel frontend auto-deploys from main; verify the homepage
     and New research panels after each deploy.
- No hosting migration was made.

## Part 9 — Mobile responsiveness (code review, not live device test)

Existing breakpoints already handle it: hero input stacks below
600px, hero/features/steps grids go 1-column below 480px, sidebar
becomes off-canvas below 800px, stats go 2-column, conflict cards
stack below `sm`/`md` (Tailwind), and the evidence graph scrolls
inside `.graph-canvas` instead of overflowing the page. Live
390px/320px device testing was NOT possible with the available
browser tools — that remains unverified, and no mobile claim is
made beyond the CSS review.

## Part 10 — Temporal classification (already implemented)

See the stabilization commit: period first, then conditions, then
scope, shared year = same_period, otherwise uncertain with a
verify-first note. Both quotes are always preserved.

## Part 11 — Security (preserved, not weakened)

SSRF blocklist + DNS + redirect re-validation, http(s) only,
10 s timeout, 1 MB fetch cap, 5 MB / 50-page PDF caps, content-type
checks, per-IP rate limits (fetch 60/min, analyze 30/min, discover
30/min) + discovery quotas above, CORS exactly the Vercel origin,
secrets server-side only, quote validation sweep, Groq receives
goal/questions only (never source text).

## Part 12 — Testing

Run: `cd backend && .venv/bin/pytest tests/ -q` and
`cd frontend && npm run build`. Results are in the final report;
do not quote them without running.
