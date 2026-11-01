import { useState } from "react";
import { Search } from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { DiscoverResult } from "../lib/types";

// Source discovery: suggestions from a configured provider only.
// Nothing here is an analyzed source until the user selects it and
// the existing fetcher reads it in /api/analyze.
export function SourceDiscovery({
  goal,
  searchConfigured,
  onAdd,
}: {
  goal: string;
  searchConfigured: boolean;
  onAdd: (urls: string[]) => void;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<DiscoverResult[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const discover = async () => {
    setError(null);
    setLoading(true);
    try {
      const response = await api.discover(query.trim() || goal.trim());
      setResults(response.results);
      setSelected(new Set());
      setSearched(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Discovery failed.");
    } finally {
      setLoading(false);
    }
  };

  if (!searchConfigured) {
    return (
      <section className="rounded-2xl border border-line bg-card p-5 shadow-card">
        <h2 className="font-display text-xl">Discover sources</h2>
        <p className="mt-1 text-sm text-inksoft">
          Source discovery is not configured on this backend (no search provider key set). Add your own links or
          pasted text below instead — GapLens never invents search results.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-line bg-card p-5 shadow-card">
      <h2 className="font-display text-xl">Discover sources</h2>
      <p className="mt-1 text-sm text-inksoft">
        Search results are suggestions only. Select the ones that look relevant, then add them — only then are
        they fetched and analyzed like any other source.
      </p>
      <div className="mt-3 flex gap-2">
        <input
          aria-label="Search for sources"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={goal ? `Search: ${goal}` : "Search for sources…"}
          className="flex-1 rounded-xl border border-line bg-paper px-3 py-2 text-sm placeholder:text-inksoft/60"
        />
        <button
          type="button"
          onClick={discover}
          disabled={loading || !(query.trim() || goal.trim())}
          className="rounded-xl bg-indigoaccent px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          <Search size={16} className="inline" /> {loading ? "Searching…" : "Search"}
        </button>
      </div>
      {error && (
        <p role="alert" className="mt-3 rounded-xl border border-coral/40 bg-coral/5 p-3 text-sm text-coral">
          {error}
        </p>
      )}
      {searched && results.length === 0 && !error && (
        <p className="mt-3 text-sm text-inksoft">No results returned for this search. Try different words.</p>
      )}
      {results.length > 0 && (
        <>
          <ul className="mt-3 space-y-2">
            {results.map((r) => (
              <li key={r.link} className="flex items-start gap-2 rounded-xl border border-line bg-paper p-3">
                <input
                  type="checkbox"
                  aria-label={`Select ${r.title}`}
                  checked={selected.has(r.link)}
                  onChange={() => {
                    const next = new Set(selected);
                    if (next.has(r.link)) next.delete(r.link);
                    else next.add(r.link);
                    setSelected(next);
                  }}
                  className="mt-1"
                />
                <div>
                  <a href={r.link} target="_blank" rel="noreferrer" className="text-sm font-semibold text-indigoaccent hover:underline">
                    {r.title}
                  </a>
                  <p className="text-xs text-inksoft">{r.link}</p>
                  {r.snippet && <p className="mt-1 text-sm">{r.snippet}</p>}
                </div>
              </li>
            ))}
          </ul>
          <button
            type="button"
            disabled={selected.size === 0}
            onClick={() => onAdd([...selected])}
            className="mt-3 rounded-xl bg-indigoaccent px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            Add {selected.size} selected {selected.size === 1 ? "source" : "sources"} to analyze
          </button>
        </>
      )}
    </section>
  );
}
