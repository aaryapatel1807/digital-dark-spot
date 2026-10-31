import { CalendarClock, ExternalLink, FlaskConical, Globe, X } from "lucide-react";
import { useEffect, useRef } from "react";
import type { AnalysisResponse, SourceRecord } from "../lib/types";

export function SourceDrawer({
  source,
  result,
  focusQuestionId,
  onClose,
}: {
  source: SourceRecord | null;
  result: AnalysisResponse | null;
  focusQuestionId?: string;
  onClose: () => void;
}) {
  const panelRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!source) return;
    // Keyboard users previously could tab out behind the drawer, and
    // focus stayed on the page behind it. Now: focus moves in, Tab
    // cycles inside the panel, Escape closes, focus returns.
    const previouslyFocused = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = Array.from(
        panelRef.current.querySelectorAll<HTMLElement>(
          "button:not([disabled]), a[href], input, textarea, [tabindex]:not([tabindex='-1'])",
        ),
      ).filter((el) => !el.hasAttribute("disabled") && el.offsetParent !== null);
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
      previouslyFocused?.focus?.();
    };
  }, [source, onClose]);

  if (!source || !result) return null;

  const evidence = result.coverage.flatMap((row) =>
    row.evidence
      .filter((quote) => quote.source_id === source.id)
      .map((quote) => ({ question: row.question, questionId: row.question_id, quote: quote.quote })),
  );
  const ok = source.fetch_status === "ok";

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label={`Source ${source.id}`}>
      <button
        type="button"
        aria-label="Close source drawer"
        onClick={onClose}
        className="drawer-backdrop absolute inset-0 h-full w-full cursor-default bg-ink/40"
      />
      <aside ref={panelRef} className="drawer-panel absolute right-0 top-0 flex h-full w-full max-w-md flex-col bg-white shadow-lift">
        <div className="flex items-start justify-between gap-3 border-b border-line p-5">
          <div className="min-w-0">
            <p className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide text-inksoft">
              <span className="rounded-full border border-line bg-cream px-2 py-0.5 normal-case tracking-normal">
                {source.id}
              </span>
              {source.is_sample ? (
                <span className="flex items-center gap-1 rounded-full border border-suggested/40 bg-suggested/10 px-2 py-0.5 normal-case tracking-normal text-suggested">
                  <FlaskConical size={12} /> Demo source
                </span>
              ) : (
                <span className="flex items-center gap-1 rounded-full border border-line bg-cream px-2 py-0.5 normal-case tracking-normal">
                  <Globe size={12} /> {source.kind === "url" ? "Fetched page" : "Pasted text"}
                </span>
              )}
            </p>
            <h2 className="mt-2 font-display text-xl leading-snug">{source.title ?? source.id}</h2>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-lg border border-line bg-white p-2 text-inksoft transition hover:border-ink/30 hover:text-ink"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto p-5">
          <dl className="space-y-2 text-sm">
            <div className="flex gap-2">
              <dt className="w-24 shrink-0 font-semibold text-inksoft">Status</dt>
              <dd>
                <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${ok ? "border-sourced/30 bg-sourced/10 text-sourced" : "border-coral/30 bg-coral/5 text-coral"}`}>
                  {source.fetch_status}
                </span>
                {source.error ? <span className="block mt-1 text-inksoft">{source.error}</span> : null}
              </dd>
            </div>
            <div className="flex gap-2">
              <dt className="w-24 shrink-0 font-semibold text-inksoft">Published</dt>
              <dd className="flex items-center gap-1.5">
                <CalendarClock size={14} className="text-inksoft" />
                {source.date_status === "known" && source.published_date
                  ? new Date(`${source.published_date}T00:00:00`).toLocaleDateString()
                  : "Unknown — no date found on the source"}
              </dd>
            </div>
            {source.url ? (
              <div className="flex gap-2">
                <dt className="w-24 shrink-0 font-semibold text-inksoft">Link</dt>
                <dd className="min-w-0">
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 break-all font-medium text-indigoaccent hover:underline"
                  >
                    {source.url} <ExternalLink size={13} className="shrink-0" />
                  </a>
                </dd>
              </div>
            ) : null}
            <div className="flex gap-2">
              <dt className="w-24 shrink-0 font-semibold text-inksoft">Text</dt>
              <dd className="text-inksoft">{source.text_length.toLocaleString()} characters collected</dd>
            </div>
          </dl>

          {source.text_excerpt ? (
            <div>
              <h3 className="text-sm font-semibold">Opening passage</h3>
              <p className="mt-2 rounded-xl border border-line bg-cream p-3 text-sm leading-relaxed text-ink/85">
                {source.text_excerpt}
              </p>
            </div>
          ) : null}

          <div>
            <h3 className="text-sm font-semibold">
              Evidence from this source ({evidence.length} passage{evidence.length === 1 ? "" : "s"})
            </h3>
            {evidence.length === 0 ? (
              <p className="mt-2 rounded-xl border border-line bg-cream p-3 text-sm text-inksoft">
                {ok
                  ? "This source supports none of the checked questions in the collected passages."
                  : "Nothing was collected from this source, so it has no passages to show."}
              </p>
            ) : (
              <div className="mt-2 space-y-3">
                {evidence.map((item, i) => (
                  <blockquote
                    key={i}
                    className={`rounded-xl border p-3 text-sm ${
                      focusQuestionId === item.questionId
                        ? "border-indigoaccent/50 bg-indigosoft"
                        : "border-line bg-cream"
                    }`}
                  >
                    <span className="font-semibold">{item.question}</span>
                    <span className="mt-1 block leading-relaxed text-ink/85">“{item.quote}”</span>
                  </blockquote>
                ))}
              </div>
            )}
          </div>

          {source.is_sample ? (
            <p className="rounded-xl border border-suggested/30 bg-suggested/5 p-3 text-xs text-inksoft">
              Demo source: bundled for the sample run. It has no real URL and describes no real page.
            </p>
          ) : null}
        </div>
      </aside>
    </div>
  );
}
