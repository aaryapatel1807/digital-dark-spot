import { ChevronRight } from "lucide-react";
import { useState } from "react";
import type { AnalysisResponse, CoverageStatus, SourceRecord } from "../lib/types";

const STATUS_PILL: Record<CoverageStatus, string> = {
  covered: "bg-sourced/10 text-sourced border-sourced/30",
  partial: "bg-suggested/10 text-suggested border-suggested/30",
  not_found: "bg-unknown/10 text-unknown border-unknown/30",
};

const STATUS_LABEL: Record<CoverageStatus, string> = {
  covered: "Covered",
  partial: "Partial",
  not_found: "Not found",
};

type Filter = "all" | CoverageStatus;

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All questions" },
  { id: "covered", label: "Covered" },
  { id: "partial", label: "Partial" },
  { id: "not_found", label: "Unanswered" },
];

export function CoverageMatrix({
  result,
  onOpenSource,
}: {
  result: AnalysisResponse;
  onOpenSource: (source: SourceRecord, focusQuestionId?: string) => void;
}) {
  const [filter, setFilter] = useState<Filter>("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const sourceById = new Map(result.sources.map((s) => [s.id, s]));
  const rows = result.coverage.filter((c) => filter === "all" || c.status === filter);

  return (
    <section className="rise-in-late rounded-2xl border border-line bg-card p-5 shadow-card sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl leading-tight">Evidence coverage matrix</h2>
          <p className="mt-1 text-sm text-inksoft">
            Rows are questions, columns are sources. A dot means that source supports the question — click it to
            open the source drawer. Click a question to read its quotes inline.
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter questions by coverage">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => setFilter(f.id)}
              aria-pressed={filter === f.id}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                filter === f.id
                  ? "border-indigoaccent bg-indigoaccent text-white"
                  : "border-line bg-card text-inksoft hover:border-indigoaccent/50 hover:text-indigoaccent"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {rows.length === 0 ? (
        <p className="mt-5 rounded-xl border border-line bg-cream p-4 text-sm text-inksoft">
          No questions match this filter for this run.
        </p>
      ) : (
        <div className="matrix-scroll mt-5 overflow-x-auto pb-1">
          <table className="w-full min-w-[640px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-line text-left">
                <th scope="col" className="min-w-[260px] py-2 pr-3 font-semibold">Question</th>
                {result.sources.map((source) => {
                  const ok = source.fetch_status === "ok";
                  return (
                    <th key={source.id} scope="col" className="px-2 py-2 text-center font-semibold">
                      <button
                        type="button"
                        onClick={() => onOpenSource(source)}
                        title={source.title ?? source.id}
                        className="rounded-lg px-2 py-1 transition hover:bg-cream"
                      >
                        <span className={`mr-1.5 inline-block h-2 w-2 rounded-full ${ok ? "bg-sourced" : "bg-coral"}`} />
                        {source.id}
                      </button>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const supporting = new Set(row.supporting_source_ids);
                const expanded = expandedId === row.question_id;
                return (
                  <tr key={row.question_id} className="border-b border-line/70 last:border-0 hover:bg-cream/50">
                    <td className="py-3 pr-3 align-top">
                      <button
                        type="button"
                        onClick={() => setExpandedId(expanded ? null : row.question_id)}
                        aria-expanded={expanded}
                        className="flex w-full items-start gap-1.5 text-left"
                      >
                        <ChevronRight
                          size={16}
                          className={`mt-0.5 shrink-0 text-inksoft transition-transform ${expanded ? "rotate-90" : ""}`}
                        />
                        <span>
                          <span className="font-medium">{row.question}</span>
                          <span className="ml-2 rounded-full border px-2 py-0.5 text-[11px] font-medium text-inksoft">
                            {row.origin === "user" ? "your question" : "derived"}
                          </span>
                          <span className={`ml-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium ${STATUS_PILL[row.status]}`}>
                            {STATUS_LABEL[row.status]}
                          </span>
                        </span>
                      </button>
                      {expanded ? (
                        row.evidence.length > 0 ? (
                          <div className="mt-2 space-y-2 pl-6">
                            {row.evidence.map((quote, i) => {
                              const source = sourceById.get(quote.source_id);
                              return (
                                <blockquote key={i} className="rounded-xl border border-line bg-cream p-3 text-sm">
                                  <button
                                    type="button"
                                    onClick={() => source && onOpenSource(source, row.question_id)}
                                    className="font-semibold text-indigoaccent hover:underline"
                                  >
                                    {quote.source_id}
                                    {source?.title ? ` · ${source.title}` : ""}
                                  </button>
                                  <span className="block mt-1 text-ink/80">“{quote.quote}”</span>
                                </blockquote>
                              );
                            })}
                          </div>
                        ) : (
                          <p className="mt-2 pl-6 text-sm text-inksoft">
                            No collected source answers this question. That is a gap in these sources, not proof
                            no answer exists.
                          </p>
                        )
                      ) : null}
                    </td>
                    {result.sources.map((source) => {
                      const ok = source.fetch_status === "ok";
                      const supports = supporting.has(source.id);
                      return (
                        <td key={source.id} className="px-2 py-3 text-center align-top">
                          {!ok ? (
                            <button
                              type="button"
                              onClick={() => onOpenSource(source)}
                              title={source.error ?? "Inaccessible source"}
                              aria-label={`${source.id} inaccessible: ${source.error ?? "could not be read"}`}
                              className="rounded-full bg-coral/10 px-2 py-0.5 text-xs font-semibold text-coral"
                            >
                              !
                            </button>
                          ) : supports ? (
                            <button
                              type="button"
                              onClick={() => onOpenSource(source, row.question_id)}
                              title={`Open ${source.id} — evidence for this question`}
                              aria-label={`Open ${source.id} evidence for ${row.question}`}
                              className={`mx-auto block h-3.5 w-3.5 rounded-full transition hover:scale-125 ${
                                row.status === "covered" ? "bg-sourced" : "bg-suggested"
                              }`}
                            />
                          ) : (
                            <span className="text-inksoft/50" aria-label="No evidence in this source">–</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-3 text-xs text-inksoft">
        Source columns in order: {result.sources.map((s) => `${s.id}${s.title ? ` · ${s.title}` : ""}`).join(" · ")}.
      </p>
    </section>
  );
}
