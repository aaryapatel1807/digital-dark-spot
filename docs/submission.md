# GapLens — Submission pack (SHINCHAN Hackathon 2026, Digital Dark Spot)

## Mandatory submission fields

- **Project name:** GapLens
- **Public GitHub repo:** https://github.com/aaryapatel1807/digital-dark-spot
- **Live demo (optional field, but live):** https://gaplens-omega.vercel.app
- **Backend (live):** https://gaplens-backend-77c25.containers.snapdeploy.app

## Detailed description (paste into Unista)

GapLens is a web platform that analyses multiple sources on one topic and
surfaces information gaps, conflicting claims, outdated or undated details,
and unanswered questions — with source references and a verify-next
checklist. It is built for the Digital Dark Spot problem: a reader should
not have to trust a single summary, or hunt across tabs to find what a
topic is missing.

How it works, in one run: the user enters a research goal, optional
questions, and up to 20 inputs — public URLs and/or pasted texts. GapLens
fetches the URLs itself (SSRF-safe, per-source failure isolation: one
blocked or dead page never kills the run), then runs a deterministic
engine over the collected text. It never invents a citation: every piece
of evidence is a verbatim quote, validated server-side as a substring of
its source before the response leaves. AI findings are labelled
"possible" throughout — the product never picks a winner between
conflicting sources.

What a report shows:

- **Coverage matrix** — per question: covered / partial / not found,
  with the supporting source for every answer.
- **Possible conflicts** — side-by-side, both quotes shown. Numeric
  conflicts cover money, percent, year, date, and bare numbers
  (for example, a CGPA of 7.0 in one source vs 7.5 in another).
  Stance conflicts cover a passage denying a term another affirms.
- **Freshness warnings** — stale sources (older than 365 days, with age
  in days) and undated sources (never guessed).
- **Gaps** — unanswered, partial, single-source-only, stale-only,
  undated-only.
- **Verify-next checklist** — ranked actions, including a trust-tier
  alert: if no readable source is official (government host), the
  report says so plainly and asks the user to find an official source.
- **Evidence drawer** — every source, its fetch status, date status,
  and evidence passages, so any finding can be checked in seconds.

Demo mode is kept strictly separate: it runs the same engine over a
bundled scholarship sample, labelled "Demo data — not a live result",
with no URLs, so a sample can never look like a citation.

## Demo script (examples the engine actually flags — use these)

Wake the backend first: open the backend `/api/health` URL and wait for
`{"status":"ok"}` — the free container sleeps after 15 minutes idle
and takes 60–90 seconds to wake.

1. **Live, CGPA conflict (verified live 1 Nov):** goal "Scholarship
   eligibility and renewal", question "What CGPA is required for
   renewal?", pasted texts "Renewal of the scholarship requires a
   CGPA of 7.0 or above." and "Renewal of the scholarship requires
   students to maintain a CGPA of 7.5 or above." Expected: 100%
   coverage, 1 possible conflict ("different number values", both
   quotes), plus the no-official-source alert.
2. **Live, money conflict:** two sources giving different fees in
   rupees (for example Rs. 10,000 vs Rs. 12,000) for the same question.
   Expected: 1 possible conflict, both quotes.
3. **Demo mode:** the bundled scholarship sample through the same
   engine, clearly labelled as demo data.

Do not demo a paraphrase-only example expecting coverage: the engine
is keyword-overlap by design (precision over recall), so a question
phrased very differently from its sources can read as "not found".
That limitation is stated in the README, not hidden.

## What was verified (not claimed)

- Backend tests: 69 passed (including 3 for bare-number conflicts and
  the no-official-source alert).
- Live health: `version 2.0.0`, `environment production`,
  `groq_configured true`, checked against the deployed SnapDeploy URL.
- Live pair: Vercel frontend header shows "Backend connected" (not
  offline), no CORS error, and a live (non-demo) report runs end to end.
- Frontend: React 18 + Vite 5 + TypeScript + Tailwind. Backend:
  Python 3.12 + FastAPI + Pydantic v2. Groq, when configured, only ever
  proposes questions — it never writes findings, summaries, or quotes.

## Honest limitations (stated, not hidden)

- Coverage is keyword-overlap, not language understanding: it favours
  precision over recall, so paraphrases can be missed.
- No database persistence yet: reports live in the browser (local
  storage) in this build; there is no re-check + diff across runs yet.
- Pages that need JavaScript to render are not executed; only served
  HTML/text is extracted.
- The free backend sleeps after 15 minutes idle (wake via `/api/health`
  before judging or demoing).
