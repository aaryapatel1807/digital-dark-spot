import type { AnalysisResponse } from "../lib/types";

// Simple view: the SAME result, in everyday language. No new numbers,
// no new conclusions — every count below is computed from the result
// the Research view shows, so the two views cannot disagree.
export function SimpleView({ result }: { result: AnalysisResponse }) {
  const covered = result.coverage.filter((c) => c.status === "covered").length;
  const partial = result.coverage.filter((c) => c.status === "partial").length;
  const missing = result.coverage.filter((c) => c.status === "not_found");
  const readable = result.sources.filter((s) => s.fetch_status === "ok" && s.text_length > 0).length;
  const failed = result.sources.filter((s) => s.fetch_status !== "ok").length;
  const stillToCheck = missing.length + partial;
  const headline =
    stillToCheck === 0
      ? "We found answers for every question in the sources you gave us — but check the conflicts and dates below before acting on them."
      : `We found useful information, but ${stillToCheck} important ${stillToCheck === 1 ? "thing" : "things"} still need${stillToCheck === 1 ? "s" : ""} checking.`;
  const cards = [
    { value: String(covered), label: "Supported answers", note: "Questions with a matching passage in your sources." },
    { value: String(missing.length + partial), label: "Missing or partial answers", note: "Not found in these sources — not proof it does not exist." },
    { value: String(result.conflicts.length), label: "Possible contradictions", note: "Two sources say different things. No winner is picked." },
    { value: String(result.freshness_warnings.length), label: "Outdated or undated sources", note: "Old or dateless sources — treat their details with care." },
  ];
  return (
    <section className="space-y-6">
      <div className="panel">
        <h2 className="font-display text-2xl leading-tight">{headline}</h2>
        <p className="mt-2 text-sm leading-relaxed text-inksoft">
          {result.goal} · Checked {result.questions_analyzed} {result.questions_analyzed === 1 ? "question" : "questions"} across {readable} source{readable === 1 ? "" : "s"} we could read
          {failed ? ` (${failed} source${failed === 1 ? "" : "s"} could not be opened)` : ""}.
          Coverage ({result.coverage_percent}%) counts questions with a strong keyword match out of all questions checked — it is not a truth score or a guarantee.
        </p>
        <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {cards.map((c) => (
            <div key={c.label} className="rounded-xl border border-line bg-card p-4">
              <p className="font-display text-3xl leading-none">{c.value}</p>
              <p className="mt-1.5 text-sm font-medium">{c.label}</p>
              <p className="text-xs text-inksoft">{c.note}</p>
            </div>
          ))}
        </div>
      </div>

      {missing.length > 0 && (
        <div className="panel">
          <h2>Something important is missing</h2>
          <p className="section-description">We could not find these in the information we checked. That does not mean they do not exist — it means these sources do not say.</p>
          <ul className="mt-3 space-y-3">
            {missing.map((c) => (
              <li key={c.question_id}>
                <strong>{c.question}</strong>
                <p className="text-sm text-inksoft">What to do: look for this on the official source for this topic, and add it as a new source to re-check.</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.conflicts.length > 0 && (
        <div className="panel">
          <h2>Sources disagree — read both sides</h2>
          <p className="section-description">These are possible differences, not verdicts. The sources may describe different years, amounts, or conditions.</p>
          <div className="mt-3 space-y-4">
            {result.conflicts.map((conflict, i) => (
              <article key={i}>
                <h3 className="text-sm font-semibold">{conflict.question}</h3>
                <div className="mt-2 grid gap-3 md:grid-cols-2">
                  {conflict.values.map((v, j) => (
                    <blockquote key={j} className="rounded-xl border border-line bg-paper p-3 text-sm">
                      <span className="source-chip">{v.source_id}</span> “{v.quote}”
                    </blockquote>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </div>
      )}

      <div className="panel">
        <h2>What should you do next?</h2>
        <p className="section-description">Start with the first item, then work down. Switch to Research view for the full evidence, dates, and checklist.</p>
        <ol className="mt-3 space-y-2">
          {result.actions.slice(0, 5).map((a) => (
            <li key={a.rank} className="text-sm">
              <strong>{a.priority} priority:</strong> {a.action} — {a.reason}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
