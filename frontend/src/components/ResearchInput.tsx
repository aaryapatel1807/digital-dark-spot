import { FlaskConical, Plus, Trash2 } from "lucide-react";

export interface ResearchForm {
  goal: string;
  questions: string[];
  urls: string[];
  texts: { title: string; text: string }[];
}

export const EMPTY_FORM: ResearchForm = {
  goal: "",
  questions: [""],
  urls: [""],
  texts: [],
};

export const RESEARCH_TEMPLATES: Record<string, string[]> = {
  Scholarship: ["Who is eligible?", "Which documents are required?", "When is the last date to apply?", "How much is awarded?", "What renews the scholarship next year?", "How do you apply, step by step?", "What restrictions or exclusions apply?", "How are applicants selected?"],
  "College Admission": ["Who is eligible to apply?", "Which documents are required?", "When is the last date to apply?", "What are the fees?", "What is the selection process?", "Is this information for the current admission cycle?"],
  "Career and Jobs": ["What is the role and salary?", "What qualifications are required?", "When is the last date to apply?", "What is the selection process?", "What should I verify before accepting this offer?"],
  "Government Schemes": ["Who is eligible?", "Which documents are required?", "When is the last date to apply?", "How much support is offered?", "Is this scheme still active?", "How do you apply?"],
  "Business Research": ["What is the product or service?", "What does it cost?", "Who is it for?", "What are the terms and conditions?", "What information is missing or uncertain?"],
  "Academic Research": ["What is the main claim?", "What evidence supports it?", "What evidence disagrees?", "When was it published or updated?", "What is missing or uncertain?"],
  "General Investigation": ["What is this about?", "Who is eligible or affected?", "What are the key dates?", "What does it require or cost?", "What is missing or uncertain?"],
};

const MAX_INPUTS = 20;

function FieldLabel({ children, hint }: { children: React.ReactNode; hint?: string }) {
  return (
    <p className="text-sm font-semibold">
      {children}
      {hint ? <span className="ml-2 font-normal text-inksoft">{hint}</span> : null}
    </p>
  );
}

function RemoveButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className="rounded-lg border border-line bg-card p-2 text-inksoft transition hover:border-coral/50 hover:text-coral"
    >
      <Trash2 size={15} />
    </button>
  );
}

function AddButton({ onClick, children, disabled }: { onClick: () => void; children: React.ReactNode; disabled?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-card px-3 py-1.5 text-sm font-medium text-inksoft transition hover:border-indigoaccent/50 hover:text-indigoaccent disabled:cursor-not-allowed disabled:opacity-40"
    >
      <Plus size={15} /> {children}
    </button>
  );
}

export function ResearchInput({
  mode,
  form,
  onChange,
  onAnalyze,
  onClear,
  analyzing,
  formError,
}: {
  mode: "live" | "demo";
  form: ResearchForm;
  onChange: (form: ResearchForm) => void;
  onAnalyze: () => void;
  onClear: () => void;
  analyzing: boolean;
  formError: string | null;
}) {
  const isDemo = mode === "demo";
  const inputCount = form.urls.filter((u) => u.trim()).length + form.texts.filter((t) => t.text.trim()).length;
  const atCap = form.urls.length + form.texts.length >= MAX_INPUTS;

  const set = (patch: Partial<ResearchForm>) => onChange({ ...form, ...patch });
  const updateList = <T,>(list: T[], index: number, value: T): T[] =>
    list.map((item, i) => (i === index ? value : item));
  const removeFrom = <T,>(list: T[], index: number): T[] => list.filter((_, i) => i !== index);

  return (
    <section className="rounded-2xl border border-line bg-card p-5 shadow-card sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl leading-tight">Research brief</h2>
          <p className="mt-1 text-sm text-inksoft">
            One goal, the sources you want checked, and the questions they should answer.
          </p>
        </div>
        <p className="rounded-full border border-line bg-cream px-3 py-1 text-xs font-medium text-inksoft">
          {inputCount} / {MAX_INPUTS} sources filled
        </p>
      </div>

      {isDemo ? (
        <p className="mt-4 flex items-start gap-2 rounded-xl border border-suggested/30 bg-suggested/5 p-3 text-sm">
          <FlaskConical size={16} className="mt-0.5 shrink-0 text-suggested" />
          <span>
            Demo mode uses the bundled scholarship sources. The fields below are shown for reference and are
            ignored until you switch back to Live.
          </span>
        </p>
      ) : null}

      <fieldset disabled={isDemo || analyzing} className="mt-5 space-y-6 disabled:opacity-60">
        <div>
          <p className="text-xs font-semibold tracking-wide text-inksoft">STEP 1 — ASK</p>
          <FieldLabel hint="Required for live analysis">Research goal</FieldLabel>
          <textarea
            aria-label="Research goal"
            value={form.goal}
            onChange={(event) => set({ goal: event.target.value })}
            rows={2}
            placeholder="e.g. Scholarship application — what does it take, and what is still unclear?"
            className="mt-2 w-full rounded-xl border border-line bg-paper px-3 py-2.5 text-sm placeholder:text-inksoft/60"
          />
        </div>

        <div>
          <p className="text-xs font-semibold tracking-wide text-inksoft">STEP 2 — CHOOSE A RESEARCH TYPE (OPTIONAL)</p>
          <p className="mt-1 text-sm text-inksoft">Pick a template to fill in the questions below. You can edit or delete any of them — nothing is forced.</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {Object.keys(RESEARCH_TEMPLATES).map((name) => (
              <button key={name} type="button" onClick={() => set({ questions: [...RESEARCH_TEMPLATES[name]] })} className="rounded-full border border-line bg-card px-3 py-1.5 text-sm font-medium text-inksoft transition hover:border-indigoaccent/50 hover:text-indigoaccent">
                {name}
              </button>
            ))}
          </div>
        </div>

        <div>
          <FieldLabel hint="Optional — left empty, questions are derived from the goal">
            Questions to check
          </FieldLabel>
          <div className="mt-2 space-y-2">
            {form.questions.map((question, i) => (
              <div key={i} className="flex gap-2">
                <input
                  aria-label={`Question ${i + 1}`}
                  value={question}
                  onChange={(event) => set({ questions: updateList(form.questions, i, event.target.value) })}
                  placeholder={`Question ${i + 1} — e.g. Who is eligible?`}
                  className="flex-1 rounded-xl border border-line bg-paper px-3 py-2 text-sm placeholder:text-inksoft/60"
                />
                {form.questions.length > 1 ? (
                  <RemoveButton onClick={() => set({ questions: removeFrom(form.questions, i) })} label={`Remove question ${i + 1}`} />
                ) : null}
              </div>
            ))}
          </div>
          <div className="mt-2">
            <AddButton onClick={() => set({ questions: [...form.questions, ""] })} disabled={form.questions.length >= 20}>
              Add question
            </AddButton>
          </div>
        </div>

        <div>
          <p className="text-xs font-semibold tracking-wide text-inksoft">STEP 3 — ADD SOURCES</p>
          <p className="mt-1 text-sm text-inksoft">Paste public webpage links, or paste copied text. Document upload (PDF and others) is not available yet — paste the text instead. GapLens checks only what you add here.</p>
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <div>
            <FieldLabel hint="Public pages only">Source URLs</FieldLabel>
            <div className="mt-2 space-y-2">
              {form.urls.map((url, i) => (
                <div key={i} className="flex gap-2">
                  <input
                    aria-label={`Source URL ${i + 1}`}
                    value={url}
                    onChange={(event) => set({ urls: updateList(form.urls, i, event.target.value) })}
                    placeholder="https://example.com/a-public-page"
                    className="flex-1 rounded-xl border border-line bg-paper px-3 py-2 text-sm placeholder:text-inksoft/60"
                  />
                  {form.urls.length > 1 || form.texts.length > 0 ? (
                    <RemoveButton onClick={() => set({ urls: removeFrom(form.urls, i) })} label={`Remove URL ${i + 1}`} />
                  ) : null}
                </div>
              ))}
            </div>
            <div className="mt-2">
              <AddButton onClick={() => set({ urls: [...form.urls, ""] })} disabled={atCap}>
                Add URL
              </AddButton>
            </div>
          </div>

          <div>
            <FieldLabel hint="Pasted text is never fetched or dated">Pasted text</FieldLabel>
            <div className="mt-2 space-y-3">
              {form.texts.map((item, i) => (
                <div key={i} className="rounded-xl border border-line bg-paper p-3">
                  <div className="flex gap-2">
                    <input
                      aria-label={`Pasted text ${i + 1} title`}
                      value={item.title}
                      onChange={(event) =>
                        set({ texts: updateList(form.texts, i, { ...item, title: event.target.value }) })
                      }
                      placeholder="Source title (optional)"
                      className="flex-1 rounded-xl border border-line bg-card px-3 py-2 text-sm placeholder:text-inksoft/60"
                    />
                    <RemoveButton
                      onClick={() => set({ texts: removeFrom(form.texts, i) })}
                      label={`Remove pasted text ${i + 1}`}
                    />
                  </div>
                  <textarea
                    aria-label={`Pasted text ${i + 1}`}
                    value={item.text}
                    onChange={(event) =>
                      set({ texts: updateList(form.texts, i, { ...item, text: event.target.value }) })
                    }
                    rows={3}
                    placeholder="Paste the text to check…"
                    className="mt-2 w-full rounded-xl border border-line bg-card px-3 py-2 text-sm placeholder:text-inksoft/60"
                  />
                </div>
              ))}
            </div>
            <div className="mt-2">
              <AddButton onClick={() => set({ texts: [...form.texts, { title: "", text: "" }] })} disabled={atCap}>
                Add pasted text
              </AddButton>
            </div>
          </div>
        </div>
      </fieldset>

      {formError ? (
        <p role="alert" className="mt-4 rounded-xl border border-coral/40 bg-coral/5 p-3 text-sm text-coral">
          {formError}
        </p>
      ) : null}

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={onAnalyze}
          disabled={analyzing}
          className="rounded-xl bg-indigoaccent px-5 py-2.5 text-sm font-semibold text-white shadow-card transition hover:bg-indigohover disabled:cursor-not-allowed disabled:opacity-60"
        >
          {analyzing ? "Analyzing…" : isDemo ? "Show demo analysis" : "Analyze sources"}
        </button>
        <button
          type="button"
          onClick={onClear}
          disabled={analyzing}
          className="rounded-xl border border-line bg-card px-4 py-2.5 text-sm font-medium text-inksoft transition hover:border-ink/30 hover:text-ink disabled:opacity-60"
        >
          Clear
        </button>
        <p className="text-xs text-inksoft">
        Public pages and pasted text only. Reports save excerpts and evidence quotes in this browser; full source text is processed per request.
        </p>
      </div>
    </section>
  );
}
