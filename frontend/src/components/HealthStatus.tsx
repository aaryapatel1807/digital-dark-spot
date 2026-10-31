import { CheckCircle2, KeyRound, WifiOff } from "lucide-react";
import type { HealthResponse } from "../lib/types";

export function HealthStatus({
  health,
  error,
}: {
  health: HealthResponse | null;
  error: string | null;
}) {
  if (error) {
    return (
      <div className="rounded-2xl border border-coral/40 bg-white p-5">
        <p className="flex items-center gap-2 font-semibold text-coral">
          <WifiOff size={18} /> Backend not reachable
        </p>
        <p className="mt-1 text-sm text-ink/70">{error}</p>
      </div>
    );
  }
  if (!health) {
    return <div className="rounded-2xl border bg-white p-5 text-sm text-ink/60">Checking backend…</div>;
  }
  return (
    <div className="rounded-2xl border bg-white p-5">
      <p className="flex items-center gap-2 font-semibold text-sourced">
        <CheckCircle2 size={18} /> Backend healthy · {health.service} {health.version}
      </p>
      <p className="mt-2 flex items-center gap-2 text-sm text-ink/70">
        <KeyRound size={15} />
        Groq key configured: <strong>{health.groq_configured ? "yes" : "no — sample mode only"}</strong>
        <span className="text-ink/50">(the key itself is never shown or sent here)</span>
      </p>
    </div>
  );
}
