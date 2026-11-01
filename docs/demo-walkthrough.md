# GapLens demo walkthrough (for judges — 2 minutes)

Live: https://gaplens-omega.vercel.app · Repo: https://github.com/aaryapatel1807/digital-dark-spot

Before starting: wake the backend at
https://gaplens-backend-77c25.containers.snapdeploy.app/api/health
(free container sleeps after 15 idle minutes; wake takes 60–90 s).
The frontend header will then read "Backend connected".

## 1. Homepage (Simple by design)

Open the homepage. Headline: "Every answer has a blind spot."
Type or pick an example — e.g. "Can I apply for this scholarship?" —
and click **Start Investigation**. The question carries into New
research; nothing is searched for you, and no source is invented.

## 2. Try an Example (labelled demo, no sources needed)

Click **Try an Example**. This runs the bundled fictional scholarship
sample through the same engine as live runs, under a "Demo data —
not a live result" banner. It describes no real scholarship.

## 3. Simple view (default on Reports)

The report opens in Simple view:

- Headline in plain words: useful information found, but N things
  still need checking.
- Four cards: supported answers, missing/partial answers, possible
  contradictions, outdated/undated sources — with the coverage
  denominator explained (questions with a strong keyword match out
  of all questions checked; not a truth score).
- "Something important is missing": renewal rules are not found in
  these sources — worded as not-found-here, never as "no renewal
  rules exist".
- "Sources disagree": the income limit differs (₹2,50,000 vs
  ₹2,00,000), both quotes side by side, no winner picked.
- "What should you do next?": the top verify-next actions.

## 4. Research view (same result, full evidence)

Switch to **Research view** on the same report: coverage matrix,
gap cards, conflict explorer (with the different-year caveat),
freshness warnings (one fresh, one stale at 800 days, one undated),
evidence graph, source library, and the full checklist with ticks
saved in this browser. Counts match Simple view exactly.

## 5. Live run (the CGPA proof)

On New research, choose Live sources and paste two texts:

- "Renewal of the scholarship requires a CGPA of 7.0 or above."
- "Renewal of the scholarship requires students to maintain a CGPA
  of 7.5 or above."

Question: "What CGPA is required for renewal?" Result (verified
live 1 Nov): 100% coverage, 1 possible conflict ("different number
values", both quotes), plus the no-official-source alert in the
summary and checklist.

## 6. Guided templates

On New research, Step 2 offers seven optional templates —
Scholarship, College Admission, Career and Jobs, Government
Schemes, Business Research, Academic Research, General
Investigation. Picking one fills editable questions; nothing is
forced, and empty questions fall back to goal-derived questions
(Groq proposes them only from the goal, or templates are used).

## What is NOT claimed in this demo

No internet search, no PDF upload, no backend persistence, no
follow-up assistant, no semantic embeddings — coverage is
keyword-overlap (with a small synonym table, including
renew/continue), so a paraphrase-only question can read as
not found. Those limits are in the README, the audit, and the
submission pack.
