import { Globe, Loader2 } from "lucide-react";
import { useState } from "react";
import { api, ApiError } from "../lib/api";
import type { FetchResponse } from "../lib/types";

export function FetchPreview() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState<FetchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.fetchUrl(url));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong fetching that URL.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-2xl border bg-white p-6">
      <h2 className="flex items-center gap-2 font-display text-xl">
        <Globe size={20} /> Fetch one public page
      </h2>
      <p className="mt-1 text-sm text-ink/70">
        Foundation step only: it fetches the page you paste and shows its title and opening text. No analysis, gap, or citation is derived from it yet.
      </p>
      <form onSubmit={submit} className="mt-4 flex flex-col gap-2 sm:flex-row">
        <input
          type="url"
          required
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://example.com/a-public-page"
          className="flex-1 rounded-xl border px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={loading}
          className="flex items-center justify-center gap-2 rounded-xl bg-ink px-4 py-2 text-sm font-semibold text-paper disabled:opacity-60"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : null}
          Fetch page
        </button>
      </form>
      {error ? <p className="mt-3 text-sm text-coral">{error}</p> : null}
      {result ? (
        <div className="mt-4 rounded-xl bg-paper p-4 text-sm">
          <p>
            <strong>Status:</strong> {result.status}
            {result.title ? (
              <>
                {" · "}<strong>Title:</strong> {result.title}
              </>
            ) : null}
          </p>
          {result.error ? <p className="mt-1 text-coral">{result.error}</p> : null}
          {result.text_excerpt ? <p className="mt-2 text-ink/80">{result.text_excerpt}…</p> : null}
          <p className="mt-2 text-xs text-ink/50">{result.note}</p>
        </div>
      ) : null}
    </section>
  );
}
