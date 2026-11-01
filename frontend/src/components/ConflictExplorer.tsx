import { Scale } from "lucide-react";
import type { AnalysisResponse, SourceRecord } from "../lib/types";

export function ConflictExplorer({
  result,
  onOpenSource,
}: {
  result: AnalysisResponse;
  onOpenSource: (source: SourceRecord, focusQuestionId?: string) => void;
}) {
  const sourceById = new Map(result.sources.map((s) => [s.id, s]));

  return (
    <section className="rise-in-late rounded-2xl border border-line bg-card p-5 shadow-card sm:p-6">
      <h2 className="flex items-center gap-2 font-display text-2xl leading-tight">
        <Scale size={22} className="text-suggested" /> Conflict explorer
      </h2>
      <p className="mt-1 text-sm text-inksoft">
        Where sources disagree, both sides are shown verbatim. GapLens never picks a winner — verify against the
        official source. Note: the engine does not compare applicable years, so two statements from different
        cycles can appear here as a possible difference; check each quote's date before treating it as a
        contradiction.
      </p>

      {result.conflicts.length === 0 ? (
        <p className="mt-5 rounded-xl border border-line bg-cream p-4 text-sm text-inksoft">
          No possible conflicts in this run. Sources that were read agree on the questions they cover, as far as
          the collected passages show.
        </p>
      ) : (
        <div className="mt-5 space-y-4">
          {result.conflicts.map((conflict) => (
            <article key={conflict.question_id} className="rounded-2xl border border-line bg-cream/60 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-suggested/40 bg-suggested/10 px-2.5 py-0.5 text-xs font-semibold text-suggested">
                  Possible conflict
                </span>
                <h3 className="font-semibold">{conflict.question}</h3>
              </div>
              <p className="mt-2 text-sm text-inksoft">{conflict.detail}</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                {conflict.values.map((value) => {
                  const source = sourceById.get(value.source_id);
                  return (
                    <blockquote key={value.source_id} className="rounded-xl border border-line bg-card p-4">
                      <button
                        type="button"
                        onClick={() => source && onOpenSource(source, conflict.question_id)}
                        className="text-sm font-semibold text-indigoaccent hover:underline"
                      >
                        {value.source_id}
                        {source?.title ? ` · ${source.title}` : ""}
                      </button>
                      <span className="mt-2 block text-sm leading-relaxed text-ink/85">“{value.quote}”</span>
                    </blockquote>
                  );
                })}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
