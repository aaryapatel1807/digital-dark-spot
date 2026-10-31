import { AlertTriangle, FlaskConical, ListChecks, Search } from "lucide-react";
import type { SampleAnalysis, SlotStatus } from "../lib/types";

const slotStyle: Record<SlotStatus, string> = {
  covered: "bg-sourced/10 text-sourced border-sourced/30",
  partial: "bg-suggested/10 text-suggested border-suggested/30",
  gap: "bg-unknown/10 text-unknown border-unknown/30",
};

export function SampleView({ sample }: { sample: SampleAnalysis }) {
  return (
    <section className="rounded-2xl border bg-white p-6">
      <p className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-suggested">
        <FlaskConical size={16} /> Offline sample · not a live result
      </p>
      <h2 className="mt-2 font-display text-2xl">{sample.topic}</h2>
      <p className="mt-1 text-sm text-ink/70">{sample.disclaimer}</p>

      <div className="mt-5">
        <p className="text-sm font-semibold">
          Coverage: {sample.coverage_percent}%{" "}
          <span className="font-normal text-ink/60">
            ({sample.slots.filter((s) => s.status !== "gap").length} of {sample.slots.length} slots have a demo source)
          </span>
        </p>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-ink/10">
          <div className="h-full bg-sourced" style={{ width: `${sample.coverage_percent}%` }} />
        </div>
      </div>

      <div className="mt-5 grid gap-2 sm:grid-cols-2">
        {sample.slots.map((slot) => (
          <div key={slot.slot} className={`rounded-xl border px-3 py-2 text-sm ${slotStyle[slot.status]}`}>
            <span className="font-semibold capitalize">{slot.slot.replace(/_/g, " ")}</span>
            <span className="text-ink/60"> — {slot.question} </span>
            <span className="font-medium">[{slot.status}]</span>
          </div>
        ))}
      </div>

      <h3 className="mt-6 flex items-center gap-2 font-semibold">
        <Search size={17} /> Potential gaps
      </h3>
      {sample.gaps.map((gap) => (
        <p key={gap.slot} className="mt-2 rounded-xl bg-unknown/5 p-3 text-sm">
          <strong>{gap.title}</strong> — {gap.detail}
        </p>
      ))}

      <h3 className="mt-6 flex items-center gap-2 font-semibold">
        <AlertTriangle size={17} /> Possible conflicts <span className="font-normal text-ink/60">(no winner picked)</span>
      </h3>
      {sample.conflicts.map((conflict) => (
        <div key={conflict.slot} className="mt-2 rounded-xl bg-suggested/5 p-3 text-sm">
          <p className="font-semibold capitalize">{conflict.slot}</p>
          <p className="text-ink/70">{conflict.detail}</p>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {conflict.values.map((value) => (
              <blockquote key={value.source_id} className="rounded-lg border bg-white p-2">
                <span className="font-semibold">{value.source_id}: {value.value}</span>
                <span className="block text-ink/70">“{value.quote}”</span>
              </blockquote>
            ))}
          </div>
        </div>
      ))}

      <h3 className="mt-6 flex items-center gap-2 font-semibold">
        <ListChecks size={17} /> Verify next
      </h3>
      <ol className="mt-2 space-y-2">
        {sample.checklist.map((item) => (
          <li key={item.rank} className="rounded-xl border p-3 text-sm">
            <strong>{item.rank}. {item.action}</strong>
            <span className="text-ink/60"> — {item.reason}</span>
          </li>
        ))}
      </ol>

      <p className="mt-5 text-xs text-ink/50">
        Demo sources: {sample.sources.map((s) => `${s.id} · ${s.label}`).join(" · ")}. None has a URL, on purpose — a sample must not look like a citation.
      </p>
    </section>
  );
}
