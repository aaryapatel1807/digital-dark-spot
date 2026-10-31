import { Eye } from "lucide-react";
import { useEffect, useState } from "react";
import { FetchPreview } from "./components/FetchPreview";
import { HealthStatus } from "./components/HealthStatus";
import { SampleView } from "./components/SampleView";
import { api, ApiError } from "./lib/api";
import type { HealthResponse, SampleAnalysis } from "./lib/types";

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [sample, setSample] = useState<SampleAnalysis | null>(null);
  const [sampleError, setSampleError] = useState<string | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch((err: unknown) => {
      setHealthError(err instanceof ApiError ? err.message : "Backend unreachable.");
    });
    api.sample().then(setSample).catch((err: unknown) => {
      setSampleError(err instanceof ApiError ? err.message : "Sample could not be loaded.");
    });
  }, []);

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <header>
        <p className="flex items-center gap-2 text-sm font-semibold uppercase tracking-widest text-ink/60">
          <span aria-hidden className="inline-block h-3 w-3 rounded-full bg-ink" />
          <Eye size={16} /> GapLens
        </p>
        <h1 className="mt-3 font-display text-4xl leading-tight sm:text-5xl">
          Find the dark spots in what you read.
        </h1>
        <p className="mt-3 text-lg text-ink/70">
          GapLens compares sources on one topic and surfaces what is missing, what disagrees, and what to verify next —
          with the evidence shown, and AI findings labelled as potential signals, never as facts.
        </p>
        <p className="mt-2 text-sm text-ink/60">
          SHINCHAN Online Hackathon 2026 · Digital Dark Spot · Foundation build — the core loop (live analysis, real database, re-check) is the next layer, not this one.
        </p>
      </header>

      <div className="mt-8 space-y-5">
        <HealthStatus health={health} error={healthError} />
        {sample ? (
          <SampleView sample={sample} />
        ) : (
          <div className="rounded-2xl border bg-white p-5 text-sm text-ink/60">
            {sampleError ?? "Loading the offline sample…"}
          </div>
        )}
        <FetchPreview />
      </div>

      <footer className="mt-8 text-xs text-ink/50">
        Foundation honesty note: this build has no search and generates no citations. Anything labelled “sample” is bundled demo
        data with no URL. A fetched page is shown as fetched text only, with no analysis attached.
      </footer>
    </main>
  );
}
