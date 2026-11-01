import { useState } from "react";
import type { AnalysisResponse } from "../lib/types";

// Questions You May Have Missed: SUGGESTIONS, not gaps and not
// facts. Each was re-checked against this report's evidence; the
// user accepts (adds it to a new investigation) or dismisses it.
export function SuggestedQuestions({
  result,
  onAdd,
}: {
  result: AnalysisResponse;
  onAdd: (question: string) => void;
}) {
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const suggestions = (result.suggested_questions ?? []).filter((s) => !dismissed.has(s.question_id));
  if (suggestions.length === 0) return null;
  return (
    <section className="panel">
      <h2>Questions you may have missed</h2>
      <p className="section-description">
        These are suggested research questions, not established facts or confirmed gaps. Each was checked against
        this report's evidence — answered ones are marked answered, not presented as missing.
      </p>
      <ul className="mt-3 space-y-3">
        {suggestions.map((s) => (
          <li key={s.question_id} className="rounded-xl border border-line bg-paper p-4">
            <p className="font-semibold">{s.question}</p>
            <p className="mt-1 text-sm text-inksoft">{s.reason}</p>
            <p className="mt-1 text-xs text-inksoft">
              Category: {s.category} · Priority: {s.priority} · Evidence status:{" "}
              {s.coverage_status === "covered"
                ? "already answered in this report"
                : s.coverage_status === "partial"
                  ? "partially answered"
                  : "not found in this report"}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="button" onClick={() => onAdd(s.question)} className="rounded-xl bg-indigoaccent px-3 py-1.5 text-sm font-semibold text-white">
                Add to investigation
              </button>
              <button
                type="button"
                onClick={() => setDismissed(new Set(dismissed).add(s.question_id))}
                className="rounded-xl border border-line px-3 py-1.5 text-sm"
              >
                Dismiss
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
