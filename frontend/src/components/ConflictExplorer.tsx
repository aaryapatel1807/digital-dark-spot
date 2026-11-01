import { Scale } from "lucide-react";
import type { AnalysisResponse, SourceRecord } from "../lib/types";
import { CONFLICT_LABELS, CONTEXTUAL_LABELS } from "../lib/types";

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
        official source. Each conflict is classified by period, conditions, and scope: a different-year difference
        is not automatically a direct contradiction, and an unclear case is labelled as needing verification.
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
              {conflict.classification && (
                <p className="mt-2 rounded-xl border border-line bg-cream px-3 py-2 text-sm font-medium">
                  {CONFLICT_LABELS[conflict.classification]}
                  {conflict.classification_note ? ` — ${conflict.classification_note}` : ""}
                </p>
              )}
              {(result.contextual_conflicts ?? [])
                .filter((c) => c.question_id === conflict.question_id)
                .map((c) => (
                  <p key={c.classification} className="mt-2 text-sm">
                    <strong>{CONTEXTUAL_LABELS[c.classification]}.</strong> {c.explanation}
                    {c.claim_a.period || c.claim_b.period ? ` Periods: ${c.claim_a.period ?? "unknown"} vs ${c.claim_b.period ?? "unknown"}.` : ""}
                    {c.claim_a.conditions.length > 0 || c.claim_b.conditions.length > 0
                      ? ` Conditions: ${c.claim_a.conditions.join(", ") || "none"} vs ${c.claim_b.conditions.join(", ") || "none"}.`
                      : ""}
                  </p>
                ))}
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
