import { useState } from "react";
import { api, ApiError } from "../lib/api";
import type { AnalysisResponse, SourceRecord } from "../lib/types";

// Ask GapLens: answers come only from this report's own evidence.
// No new facts are written; unanswerable questions are refused.
export function AskGapLens({
  result,
  onOpenSource,
}: {
  result: AnalysisResponse;
  onOpenSource: (source: SourceRecord, focusQuestionId?: string) => void;
}) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<{
    answered: boolean;
    answer: string;
    citations: { source_id: string; quote: string }[];
    related_conflict_questions: string[];
    suggested_actions: string[];
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ask = async () => {
    setError(null);
    setLoading(true);
    try {
      setAnswer(await api.ask(question.trim(), result));
    } catch (e) {
      // Task 2: the live backend may predate /api/ask (404/405).
      // Say so plainly instead of showing a misleading generic error
      // or pretending the assistant answered.
      setError(
        e instanceof ApiError && (e.status === 404 || e.status === 405)
          ? "Ask GapLens is not available on this backend yet — it needs the GapLens 2.0 backend. The report above is still fully usable."
          : e instanceof ApiError
            ? e.message
            : "Ask GapLens failed.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="panel">
      <h2>Ask GapLens</h2>
      <p className="section-description">
        Ask about this investigation. Answers use only this report's validated evidence, with citations. If the
        evidence does not cover your question, it will say so instead of guessing.
      </p>
      <div className="mt-3 flex gap-2">
        <input
          aria-label="Ask a follow-up question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. Why is renewal important? Which source should I verify?"
          className="flex-1 rounded-xl border border-line bg-paper px-3 py-2 text-sm placeholder:text-inksoft/60"
        />
        <button
          type="button"
          onClick={ask}
          disabled={loading || question.trim().length < 3}
          className="rounded-xl bg-indigoaccent px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {loading ? "Checking evidence…" : "Ask"}
        </button>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {["Why is this information important?", "Which source should I verify?", "Explain this in simple words."].map(
          (q) => (
            <button key={q} type="button" onClick={() => setQuestion(q)} className="rounded-full border border-line bg-card px-3 py-1 text-xs font-medium text-inksoft">
              {q}
            </button>
          ),
        )}
      </div>
      {error && (
        <p role="alert" className="mt-3 rounded-xl border border-coral/40 bg-coral/5 p-3 text-sm text-coral">
          {error}
        </p>
      )}
      {answer && (
        <div className="mt-4 space-y-3" aria-live="polite">
          <p className="text-sm leading-relaxed">{answer.answer}</p>
          {answer.citations.length > 0 && (
            <div className="space-y-2">
              {answer.citations.map((c, i) => {
                const source = result.sources.find((s) => s.id === c.source_id);
                return (
                  <blockquote key={i} className="rounded-xl border border-line bg-paper p-3 text-sm">
                    <button
                      type="button"
                      onClick={() => source && onOpenSource(source)}
                      className="source-chip"
                    >
                      {c.source_id}
                    </button>{" "}
                    “{c.quote}”
                  </blockquote>
                );
              })}
            </div>
          )}
          {answer.related_conflict_questions.length > 0 && (
            <p className="text-sm text-inksoft">
              Related disagreement in this report: {answer.related_conflict_questions.join("; ")}
            </p>
          )}
          {answer.suggested_actions.length > 0 && (
            <p className="text-sm text-inksoft">Next checks: {answer.suggested_actions.join(" · ")}</p>
          )}
        </div>
      )}
    </section>
  );
}
