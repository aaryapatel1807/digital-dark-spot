import { AlertTriangle, CheckCircle2, CircleSlash, FlaskConical, MinusCircle } from "lucide-react";
import type { AnalysisResponse } from "../lib/types";

function Stat({ value, label, sub }: { value: string; label: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-line bg-white p-4">
      <p className="font-display text-3xl leading-none">{value}</p>
      <p className="mt-1.5 text-sm font-medium">{label}</p>
      {sub ? <p className="text-xs text-inksoft">{sub}</p> : null}
    </div>
  );
}

export function Overview({ result }: { result: AnalysisResponse }) {
  const covered = result.coverage.filter((c) => c.status === "covered").length;
  const partial = result.coverage.filter((c) => c.status === "partial").length;
  const unanswered = result.coverage.filter((c) => c.status === "not_found").length;
  const accessible = result.sources.filter((s) => s.fetch_status === "ok").length;
  const analyzed = new Date(result.analyzed_at).toLocaleString();

  return (
    <section className="rise-in">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-display text-2xl leading-tight">{result.goal}</h2>
        <p className="text-xs text-inksoft">
          {result.analysis_method === "deterministic+groq_questions"
            ? "Deterministic engine · questions proposed by Groq"
            : "Deterministic engine"}
          {" · "}
          {analyzed}
        </p>
      </div>
      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-inksoft">{result.summary}</p>

      <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat value={`${result.coverage_percent}%`} label="Coverage" sub={`${covered} covered · ${partial} partial`} />
        <Stat value={String(result.questions_analyzed)} label="Questions checked" sub={`${unanswered} unanswered`} />
        <Stat value={String(result.conflicts.length)} label="Possible conflicts" sub="Shown with both quotes" />
        <Stat value={String(accessible)} label="Sources read" sub={`${result.inaccessible_source_ids.length} inaccessible`} />
        <Stat value={String(result.actions.length)} label="Verify-next actions" sub="Ranked by priority" />
      </div>

      <div className="mt-4">
        <div className="h-2 overflow-hidden rounded-full bg-ink/10" role="img" aria-label={`Coverage ${result.coverage_percent}%`}>
          <div className="h-full rounded-full bg-sourced transition-all" style={{ width: `${result.coverage_percent}%` }} />
        </div>
        <div className="mt-2 flex flex-wrap gap-4 text-xs text-inksoft">
          <span className="flex items-center gap-1.5"><CheckCircle2 size={13} className="text-sourced" /> Covered</span>
          <span className="flex items-center gap-1.5"><MinusCircle size={13} className="text-suggested" /> Partial</span>
          <span className="flex items-center gap-1.5"><CircleSlash size={13} className="text-unknown" /> Not found in these sources</span>
          <span className="flex items-center gap-1.5"><AlertTriangle size={13} className="text-suggested" /> Possible conflict — no winner picked</span>
          {result.mode === "offline_sample" ? (
            <span className="flex items-center gap-1.5"><FlaskConical size={13} className="text-suggested" /> Demo data</span>
          ) : null}
        </div>
      </div>

      {result.notes.length > 0 ? (
        <div className="mt-4 space-y-1">
          {result.notes.map((note, i) => (
            <p key={i} className="rounded-xl border border-line bg-cream px-3 py-2 text-xs text-inksoft">
              Note: {note}
            </p>
          ))}
        </div>
      ) : null}
    </section>
  );
}
