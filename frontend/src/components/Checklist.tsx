import { Check, Copy, ListChecks, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import type { AnalysisResponse, Priority, SourceRecord } from "../lib/types";

const PRIORITY_STYLE: Record<Priority, string> = {
  high: "bg-coral/10 text-coral border-coral/30",
  medium: "bg-suggested/10 text-suggested border-suggested/30",
  low: "bg-unknown/10 text-unknown border-unknown/30",
};

export function Checklist({
  result,
  onOpenSource,
  done,
  onChange,
}: {
  result: AnalysisResponse;
  onOpenSource: (source: SourceRecord) => void;
  done: Set<number>;
  onChange: (done: Set<number>) => void;
}) {
  const [filter, setFilter] = useState('all');
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);
  const sourceById = new Map(result.sources.map((s) => [s.id, s]));
  const visibleActions = result.actions.filter(a => filter === 'all' || (filter === 'pending' ? !done.has(a.rank) : filter === 'completed' ? done.has(a.rank) : a.priority === 'high'));

  // Ticks belong to one report. Without this, running a second
  // analysis kept the first report's ticks (same ranks, different
  // actions) and the "x of y checked" count lied about the new run.
  useEffect(() => {
    setCopied(false);
    setCopyFailed(false);
  }, [result]);

  const toggle = (rank: number) => {
      const next = new Set(done);
      if (next.has(rank)) {
        next.delete(rank);
      } else {
        next.add(rank);
      }
      onChange(next);
  };

  const copy = async () => {
    const lines = result.actions.map(
      (a) => `${a.rank}. [${a.priority}] ${a.action} — ${a.reason}`,
    );
    const text = lines.join("\n");
    setCopyFailed(false);
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Headless browsers and locked-down permissions can refuse the
      // async clipboard API; fall back to the classic select + copy.
      try {
        const area = document.createElement("textarea");
        area.value = text;
        area.style.position = "fixed";
        area.style.opacity = "0";
        document.body.appendChild(area);
        area.select();
        const ok = document.execCommand("copy");
        document.body.removeChild(area);
        if (!ok) throw new Error("execCommand copy failed");
      } catch {
        setCopyFailed(true);
        return;
      }
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="rise-in-late rounded-2xl border border-line bg-card p-5 shadow-card sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 font-display text-2xl leading-tight">
            <ListChecks size={22} /> Verify next
          </h2>
          <p className="mt-1 text-sm text-inksoft">
            Ranked from what blocks a decision to what merely deserves a second look. Ticks are yours alone —
            they are saved with this report in your browser. A tick records your review, not proof a claim is true.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={copy}
            className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-card px-3 py-2 text-sm font-medium text-inksoft transition hover:border-indigoaccent/50 hover:text-indigoaccent"
          >
            {copied ? <Check size={15} className="text-sourced" /> : <Copy size={15} />}
            {copied ? "Copied" : "Copy list"}
          </button>
          <button
            type="button"
            onClick={() => onChange(new Set())}
            className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-card px-3 py-2 text-sm font-medium text-inksoft transition hover:border-indigoaccent/50 hover:text-indigoaccent"
          >
            <RotateCcw size={15} /> Reset ticks
          </button>
        </div>
      </div>

      <p className="mt-3 text-xs font-medium text-inksoft" role="status">
        {done.size} of {result.actions.length} checked by you
      </p>
      <progress className="check-progress" value={done.size} max={result.actions.length || 1} aria-label="Verification progress" />
      <select className="mt-3" aria-label="Filter verification tasks" value={filter} onChange={e => setFilter(e.target.value)}>
        <option value="all">All tasks</option><option value="pending">Pending</option><option value="completed">Completed</option><option value="high">High priority</option>
      </select>
      {copyFailed ? (
        <p role="alert" className="mt-2 rounded-xl border border-coral/40 bg-coral/5 p-3 text-sm text-coral">
          Copy was blocked by this browser. Select the list below by hand instead — the full text is in the
          actions above.
        </p>
      ) : null}

      {result.actions.length === 0 ? (
        <p className="mt-3 rounded-xl border border-line bg-cream p-4 text-sm text-inksoft">
          Nothing to verify next: every question is covered, no conflicts were found, and every source was read.
        </p>
      ) : visibleActions.length === 0 ? <p className="empty-copy">No tasks match this filter.</p> : (
        <ol className="mt-3 space-y-2">
          {visibleActions.map((action) => {
            const checked = done.has(action.rank);
            return (
              <li
                key={action.rank}
                className={`flex items-start gap-3 rounded-xl border p-3.5 transition ${
                  checked ? "border-sourced/30 bg-sourced/5" : "border-line bg-card"
                }`}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggle(action.rank)}
                  aria-label={`Mark done: ${action.action}`}
                  className="mt-1 h-4 w-4 shrink-0 accent-[#2e7d4f]"
                />
                <div className="min-w-0 flex-1">
                  <p className={`text-sm ${checked ? "text-inksoft line-through" : ""}`}>
                    <span className="mr-2 font-bold text-inksoft">{action.rank}.</span>
                    <span className="font-semibold">{action.action}</span>
                  </p>
                  <p className="mt-0.5 text-sm text-inksoft">{action.reason}</p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${PRIORITY_STYLE[action.priority]}`}>
                      {action.priority} priority
                    </span>
                    {action.source_ids.map((id) => {
                      const source = sourceById.get(id);
                      return source ? (
                        <button
                          key={id}
                          type="button"
                          onClick={() => onOpenSource(source)}
                          className="rounded-full border border-line bg-cream px-2 py-0.5 text-[11px] font-medium text-indigoaccent hover:underline"
                        >
                          {id}
                        </button>
                      ) : null;
                    })}
                  </div>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
