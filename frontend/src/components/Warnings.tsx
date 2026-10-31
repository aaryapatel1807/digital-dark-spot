import { Clock, HelpCircle, WifiOff } from "lucide-react";
import type { AnalysisResponse, SourceRecord } from "../lib/types";

export function Warnings({
  result,
  onOpenSource,
}: {
  result: AnalysisResponse;
  onOpenSource: (source: SourceRecord) => void;
}) {
  const sourceById = new Map(result.sources.map((s) => [s.id, s]));
  const inaccessible = result.sources.filter((s) => s.fetch_status !== "ok");
  const hasAny = result.freshness_warnings.length > 0 || inaccessible.length > 0;

  return (
    <section className="rise-in-late rounded-2xl border border-line bg-white p-5 shadow-card sm:p-6">
      <h2 className="font-display text-2xl leading-tight">Freshness &amp; uncertainty</h2>
      <p className="mt-1 text-sm text-inksoft">
        Dates are taken from the pages themselves. A source without a date is reported as unknown, never guessed.
      </p>

      {!hasAny ? (
        <p className="mt-5 rounded-xl border border-line bg-cream p-4 text-sm text-inksoft">
          No freshness warnings and no inaccessible sources in this run. Every source that was read carries a date
          within the last year.
        </p>
      ) : null}

      {result.freshness_warnings.length > 0 ? (
        <ul className="mt-5 space-y-2">
          {result.freshness_warnings.map((warning) => {
            const source = sourceById.get(warning.source_id);
            return (
              <li key={warning.source_id} className="flex items-start gap-3 rounded-xl border border-line bg-cream/60 p-3 text-sm">
                {warning.kind === "stale" ? (
                  <Clock size={17} className="mt-0.5 shrink-0 text-suggested" />
                ) : (
                  <HelpCircle size={17} className="mt-0.5 shrink-0 text-unknown" />
                )}
                <span>
                  <button
                    type="button"
                    onClick={() => source && onOpenSource(source)}
                    className="font-semibold text-indigoaccent hover:underline"
                  >
                    {warning.source_id}
                    {source?.title ? ` · ${source.title}` : ""}
                  </button>
                  <span className="text-inksoft"> — {warning.detail}</span>
                </span>
              </li>
            );
          })}
        </ul>
      ) : null}

      {inaccessible.length > 0 ? (
        <div className="mt-5">
          <h3 className="flex items-center gap-2 text-sm font-semibold">
            <WifiOff size={16} className="text-coral" /> Inaccessible sources ({inaccessible.length})
          </h3>
          <ul className="mt-2 space-y-2">
            {inaccessible.map((source) => (
              <li key={source.id} className="flex flex-wrap items-start gap-x-3 gap-y-1 rounded-xl border border-coral/25 bg-coral/5 p-3 text-sm">
                <button
                  type="button"
                  onClick={() => onOpenSource(source)}
                  className="font-semibold text-indigoaccent hover:underline"
                >
                  {source.id}
                  {source.title ? ` · ${source.title}` : ""}
                </button>
                <span className="rounded-full border border-coral/40 px-2 py-0.5 text-[11px] font-semibold text-coral">
                  {source.fetch_status}
                </span>
                <span className="text-inksoft">{source.error ?? "Could not be read."}</span>
                {source.url ? (
                  <span className="w-full truncate text-xs text-inksoft">{source.url}</span>
                ) : null}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-inksoft">
            Fix the address or replace the source, then run the analysis again. A failed fetch is never treated as
            “unchanged” or “no answer”.
          </p>
        </div>
      ) : null}
    </section>
  );
}
