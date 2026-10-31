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
}: {
  result: AnalysisResponse;
  onOpenSource: (source: SourceRecord) => void;
}) {
  const [done, setDone] = useState<Set<number>>(new Set());
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);
  const sourceById = new Map(result.sources.map((s) => [s.id, s]));

  // Ticks belong to one report. Without this, running a second
  // analysis kept the first report's ticks (same ranks, different
  // actions) and the "x of y checked" count lied about the new run.
  useEffect(() => {
    setDone(new Set());
    setCopied(false);
    setCopyFailed(false);
  }, [result]);

  const toggle = (rank: number) => {
    setDone((prev) => {
      const next = new Set(prev);
      if (next.has(rank)) {
        next.delete(rank);
      } else {
        next.add(rank);
      }
      return next;
    });
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
    <section className="rise-in-late rounded-2xl border border-line bg-white p-5 shadow-card sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 font-display text-2xl leading-tight">
            <ListChecks size={22} /> Verify next
          </h2>
          <p className="mt-1 text-sm text-inksoft">
            Ranked from what blocks a decision to what merely deserves a second look. Ticks are yours alone —
            they are kept in this browser tab and never sent anywhere.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={copy}
            className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-white px-3 py-2 text-sm font-medium text-inksoft transition hover:border-indigoaccent/50 hover:text-indigoaccent"
          >
            {copied ? <Check size={15} className="text-sourced" /> : <Copy size={15} />}
            {copied ? "Copied" : "Copy list"}
          </button>
          <button
            type="button"
            onClick={() => setDone(new Set())}
            className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-white px-3 py-2 text-sm font-medium text-inksoft transition hover:border-indigoaccent/50 hover:text-indigoaccent"
          >
            <RotateCcw size={15} /> Reset ticks
          </button>
        </div>
      </div>

      <p className="mt-3 text-xs font-medium text-inksoft" role="status">
        {done.size} of {result.actions.length} checked by you
      </p>
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
      ) : (
        <ol className="mt-3 space-y-2">
          {result.actions.map((action) => {
            const checked = done.has(action.rank);
            return (
              <li
                key={action.rank}
                className={`flex items-start gap-3 rounded-xl border p-3.5 transition ${
                  checked ? "border-sourced/30 bg-sourced/5" : "border-line bg-white"
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
