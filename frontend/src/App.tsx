import { BookOpen, Eye, FlaskConical, Loader2, RotateCcw, WifiOff } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Checklist } from "./components/Checklist";
import { ConflictExplorer } from "./components/ConflictExplorer";
import { CoverageMatrix } from "./components/CoverageMatrix";
import { Overview } from "./components/Overview";
import { EMPTY_FORM, ResearchInput, type ResearchForm } from "./components/ResearchInput";
import { SourceDrawer } from "./components/SourceDrawer";
import { Warnings } from "./components/Warnings";
import { api, ApiError } from "./lib/api";
import type {
  AnalysisResponse,
  AnalyzeRequest,
  HealthResponse,
  SourceRecord,
} from "./lib/types";

type Phase = "idle" | "loading" | "error" | "done";
type Mode = "live" | "demo";

export default function App() {
  const [mode, setMode] = useState<Mode>("live");
  const [form, setForm] = useState<ResearchForm>(EMPTY_FORM);
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [lastPayload, setLastPayload] = useState<AnalyzeRequest | null>(null);
  const [drawer, setDrawer] = useState<{ source: SourceRecord; focusQuestionId?: string } | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  const checkHealth = useCallback(() => {
    setHealthError(null);
    api
      .health()
      .then(setHealth)
      .catch((err: unknown) => {
        setHealth(null);
        setHealthError(err instanceof ApiError ? err.message : "Backend unreachable.");
      });
  }, []);

  useEffect(checkHealth, [checkHealth]);

  const runAnalysis = useCallback(async (payload: AnalyzeRequest) => {
    setPhase("loading");
    setError(null);
    setResult(null);
    setLastPayload(payload);
    try {
      const response = await api.analyze(payload);
      setResult(response);
      setPhase("done");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong while analyzing.");
      setPhase("error");
    }
  }, []);

  const submit = () => {
    setFormError(null);
    if (mode === "demo") {
      void runAnalysis({ mode: "offline_sample" });
      return;
    }
    const goal = form.goal.trim();
    if (goal.length < 3) {
      setFormError("Add a research goal of at least 3 characters.");
      return;
    }
    const urls = form.urls.map((u) => u.trim()).filter(Boolean);
    const badUrl = urls.find((u) => !/^https?:\/\//i.test(u));
    if (badUrl) {
      setFormError(`URLs must start with http:// or https:// — check “${badUrl}”.`);
      return;
    }
    const texts = form.texts
      .filter((t) => t.text.trim())
      .map((t) => (t.title.trim() ? { title: t.title.trim(), text: t.text } : { text: t.text }));
    if (urls.length + texts.length === 0) {
      setFormError("Add at least one source URL or pasted text to analyze.");
      return;
    }
    if (urls.length + texts.length > 20) {
      setFormError("At most 20 sources per analysis — remove some URLs or pasted texts.");
      return;
    }
    const questions = form.questions.map((q) => q.trim()).filter(Boolean);
    void runAnalysis({
      mode: "live",
      goal,
      ...(questions.length > 0 ? { questions } : {}),
      ...(urls.length > 0 ? { urls } : {}),
      ...(texts.length > 0 ? { texts } : {}),
    });
  };

  const switchMode = (next: Mode) => {
    setMode(next);
    setResult(null);
    setPhase("idle");
    setError(null);
    setFormError(null);
  };

  const clearAll = () => {
    setForm(EMPTY_FORM);
    setResult(null);
    setPhase("idle");
    setError(null);
    setFormError(null);
  };

  const openSource = (source: SourceRecord, focusQuestionId?: string) =>
    setDrawer({ source, focusQuestionId });

  const liveInputCount =
    form.urls.filter((u) => u.trim()).length + form.texts.filter((t) => t.text.trim()).length;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-line bg-paper/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <p className="flex items-center gap-2">
            <span aria-hidden className="flex h-8 w-8 items-center justify-center rounded-lg bg-ink text-paper">
              <Eye size={17} />
            </span>
            <span className="font-display text-xl font-bold leading-none">GapLens</span>
            <span className="hidden text-sm text-inksoft sm:inline">Research intelligence</span>
          </p>
          {health ? (
            <p className="flex items-center gap-2 rounded-full border border-line bg-white px-3 py-1.5 text-xs font-medium">
              <span className="h-2 w-2 rounded-full bg-sourced" />
              Backend connected · {health.service} {health.version}
            </p>
          ) : (
            <p className="flex items-center gap-2 rounded-full border border-coral/40 bg-white px-3 py-1.5 text-xs font-medium text-coral">
              <WifiOff size={13} />
              {healthError ?? "Checking backend…"}
              <button type="button" onClick={checkHealth} className="font-semibold underline">
                Retry
              </button>
            </p>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 pb-16">
        <section className="pt-8">
          <h1 className="max-w-2xl font-display text-4xl leading-tight sm:text-5xl">
            Find the dark spots in what you read.
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-relaxed text-inksoft">
            GapLens compares sources on one topic and surfaces what is missing, what disagrees, and what to verify
            next — with the evidence shown, and findings labelled as potential signals, never as facts.
          </p>

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <div className="inline-flex rounded-xl border border-line bg-white p-1 shadow-card" role="group" aria-label="Analysis mode">
              <button
                type="button"
                onClick={() => switchMode("live")}
                aria-pressed={mode === "live"}
                className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
                  mode === "live" ? "bg-indigoaccent text-white" : "text-inksoft hover:text-ink"
                }`}
              >
                Live analysis
              </button>
              <button
                type="button"
                onClick={() => switchMode("demo")}
                aria-pressed={mode === "demo"}
                className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold transition ${
                  mode === "demo" ? "bg-indigoaccent text-white" : "text-inksoft hover:text-ink"
                }`}
              >
                <FlaskConical size={15} /> Demo sample
              </button>
            </div>
            <p className="text-sm text-inksoft">
              {mode === "live"
                ? "Runs against the real backend and the sources you supply."
                : "Bundled scholarship demo — nothing is fetched, and no real page is described."}
            </p>
          </div>
        </section>

        <div id="research-input" className="mt-6 scroll-mt-24">
          <ResearchInput
            mode={mode}
            form={form}
            onChange={setForm}
            onAnalyze={submit}
            onClear={clearAll}
            analyzing={phase === "loading"}
            formError={formError}
          />
        </div>

        {phase === "loading" ? (
          <section className="mt-6 rounded-2xl border border-line bg-white p-6 shadow-card" role="status">
            <p className="flex items-center gap-2 font-semibold">
              <Loader2 size={18} className="animate-spin text-indigoaccent" /> Analyzing…
            </p>
            <p className="mt-1 text-sm text-inksoft">
              {mode === "demo"
                ? "Loading the bundled demo through the analysis engine."
                : `Contacting the backend and reading ${liveInputCount} source${liveInputCount === 1 ? "" : "s"}. This view waits for the full result — no partial progress is shown.`}
            </p>
            <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-ink/10">
              <div className="loading-sweep h-full w-2/5 rounded-full bg-indigoaccent/70" />
            </div>
          </section>
        ) : null}

        {phase === "error" ? (
          <section className="mt-6 rounded-2xl border border-coral/40 bg-white p-6 shadow-card" role="alert">
            <h2 className="font-display text-2xl">Analysis failed</h2>
            <p className="mt-2 text-sm text-inksoft">{error}</p>
            <p className="mt-1 text-sm text-inksoft">
              Nothing was saved and no result is shown. Your inputs are still above — fix them or try again.
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => lastPayload && void runAnalysis(lastPayload)}
                disabled={!lastPayload}
                className="inline-flex items-center gap-2 rounded-xl bg-indigoaccent px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigohover disabled:opacity-60"
              >
                <RotateCcw size={15} /> Retry
              </button>
              <button
                type="button"
                onClick={() => document.getElementById("research-input")?.scrollIntoView({ behavior: "smooth" })}
                className="rounded-xl border border-line bg-white px-4 py-2.5 text-sm font-medium text-inksoft transition hover:text-ink"
              >
                Edit inputs
              </button>
            </div>
          </section>
        ) : null}

        {phase === "idle" && !result ? (
          <section className="mt-6 rounded-2xl border border-dashed border-line bg-cream/60 p-8 text-center">
            <BookOpen size={26} className="mx-auto text-inksoft" />
            <h2 className="mt-3 font-display text-2xl">No analysis yet</h2>
            <p className="mx-auto mt-1 max-w-md text-sm text-inksoft">
              Fill in the brief above and run an analysis, or look at the demo first to see the shape of a result
              before spending a live run.
            </p>
            <button
              type="button"
              onClick={() => {
                switchMode("demo");
                void runAnalysis({ mode: "offline_sample" });
              }}
              className="mt-4 inline-flex items-center gap-2 rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-paper transition hover:opacity-90"
            >
              <FlaskConical size={15} /> Try the demo
            </button>
          </section>
        ) : null}

        {result ? (
          <div className="mt-8 space-y-6">
            {result.mode === "offline_sample" ? (
              <section className="flex items-start gap-3 rounded-2xl border border-suggested/40 bg-suggested/10 p-4" role="note">
                <FlaskConical size={19} className="mt-0.5 shrink-0 text-suggested" />
                <div className="text-sm">
                  <p className="font-semibold text-suggested">Demo data — not a live result</p>
                  <p className="mt-0.5 text-inksoft">{result.disclaimer}</p>
                </div>
              </section>
            ) : null}

            <Overview result={result} />
            <CoverageMatrix result={result} onOpenSource={openSource} />
            <ConflictExplorer result={result} onOpenSource={openSource} />
            <Warnings result={result} onOpenSource={(source) => openSource(source)} />
            <Checklist result={result} onOpenSource={(source) => openSource(source)} />

            <section className="rounded-2xl border border-line bg-cream/60 p-5 text-sm text-inksoft">
              <p>
                <strong className="text-ink">About this result.</strong> {result.disclaimer}
              </p>
              <p className="mt-1">
                Quotes are verbatim passages from the collected text. A question marked “not found” means these
                sources do not answer it — not that no answer exists anywhere.
              </p>
            </section>
          </div>
        ) : null}

        <footer className="mt-10 border-t border-line pt-5 text-xs leading-relaxed text-inksoft">
          <p>
            SHINCHAN Online Hackathon 2026 · Digital Dark Spot. GapLens never generates citations: a source is
            cited only when its text was actually collected, with the exact quote attached. Findings say
            “potential gap” and “possible conflict” — the product never picks a winner between sources.
          </p>
        </footer>
      </main>

      <SourceDrawer
        source={drawer?.source ?? null}
        result={result}
        focusQuestionId={drawer?.focusQuestionId}
        onClose={() => setDrawer(null)}
      />
    </div>
  );
}
