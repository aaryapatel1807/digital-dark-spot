# DigiDoor starter checklist — GapLens (foundation)

The 11 starter templates: the 10 DigiDoor repos + the gstack process layer.
Applied 31 Oct 2026 at the GapLens foundation build. Nothing is silently dropped:
each item below is APPLIED, LIMITED, or DELIBERATELY SKIPPED, with what it changed
in this repo. Third-party repos are credited here as inspiration/standards only —
no repo's code is copied into GapLens, and no licence was needed because nothing
was installed from them. (Aarya's standing rule: read a repo's README + licence
before installing anything from it.)

## 1. REA — APPLIED (adapted, not copied)
Studied first: the problem statement's scholarship example and the earlier
Digital Dark Spot prototype's flow (intake → sources → coverage matrix → gaps →
checklist). Borrowed structures only: the coverage-slot model, the gap/conflict/
checklist result shape, and the sourced-vs-suggested-vs-unknown evidence language.
No other product's UI, copy, logos, or assets are used. The earlier prototype's
code was NOT copied: this is a clean rewrite (React + Vite + FastAPI, replacing
the earlier Next.js build, which remains preserved on local branches
`backup-main` / `layer3-wip` and in the 31 Oct tarball — see README history note
in the final report, not in the shipped code).

## 2. Ponytail — APPLIED
Clean, minimal code as a standard: backend split into exactly one module per job
(`config`, `schemas`, `sample`, `fetcher`, `main`); frontend split into typed
client (`lib/api.ts`), mirrored types (`lib/types.ts`), and three small
components. No duplicated slot/conflict logic, no framework beyond the stated
stack. If a second template needs code changes outside a data file, that is a
bug in this layering to fix first — the same rule the earlier build set.

## 3. Hallmark — APPLIED
Distinctive "dark spot" identity, not generic gradient cards: ink-on-paper
palette (`paper #faf7f0`, `ink #1a1a18`), a literal spot mark (●) beside the
wordmark, serif display headings, and the three-colour evidence language
(green = sourced, amber = suggested, grey = unknown) that is itself part of
the product's meaning. Tokens live once in `frontend/tailwind.config.js`.

## 4. Humanizer — APPLIED
Plain, human copy throughout: "Potential gap", "Possible conflict", "Backend
not reachable — is it running on…?", "Fetched live from the URL you supplied."
Errors explain what happened and what the user can do next. No AI-sounding
filler, no "delve", no hype about what the foundation cannot yet do.

## 5. Onyx — DELIBERATELY SKIPPED (foundation)
No document-chat feature exists in GapLens. A chat would duplicate the
coverage/checklist job and cost judging marks by diluting the core loop.
Revisit only if an "ask a follow-up about a gap" feature is added later.

## 6. Impeccable — APPLIED (light polish pass, after core works)
Polish after the build works, not instead of it: spacing scale, card radius,
responsive stacking (sample grid collapses to one column), visible focus rings
on every interactive element, and hover/disabled states on the fetch button.
Full visual polish pass is scheduled again after the analysis layer lands.

## 7. UI UX Pro Max — APPLIED
Design system set upfront, before screens: tokens in `tailwind.config.js`
(ink, paper, sourced, suggested, unknown, coral, gold, teal), shared card
patterns in the components, and one page layout (`max-w-3xl`, stacked sections).
Every screen in this foundation uses them; no ad-hoc colours or radii.

## 8. Last 30 Days — APPLIED (as a note, not a scrape)
The patterns this foundation is built for are current: RAG-style grounding
(quote must come from fetched text), ALCE-style citation thinking, atomic
claims, and freshness handling (FreshQA/TimeQA-style cycle awareness). Stale
patterns — keyword-only summaries and un-cited LLM answers — are deliberately
not built in. No trend content is baked into the UI, so nothing here can go
stale with a trend cycle.

## 9. Scrapling — DELIBERATELY LIMITED
Only user-provided public URLs are fetched (`backend/app/fetcher.py`), with a
plain User-Agent, a 10-second timeout, a 1 MB cap, and no paywall bypass, no
login, no bulk crawling, no search. Blocked/paywalled pages produce a clear
message and a marked result. The target site's terms and robots rules are to
be respected; the hostname guard is basic (see README limitations).

## 10. Diagram Design — APPLIED
`docs/architecture.html` is a single portable HTML+SVG diagram of the
foundation architecture. The same diagram is summarised in the README layout
section.

## 11. gstack process layer — APPLIED, instruction-only
No Claude Code commands, no `./setup`, no paid parts (₹0 only). Think (this
checklist + README architecture) → Plan (foundation, then analysis layer, then
persistence/re-check, then export/submit) → Build → Review (this checklist +
build checks) → Test (backend honesty tests + frontend build) → Ship (clean
repo, local commit first, push only on Aarya's word) → Reflect (post-deadline
work on a separate branch only; the submitted repo stays clean and working).
Safety throughout: no force-push of the default branch — the earlier branches
and tarball are preserved untouched by this rebuild.
