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
  const [cached, setCached] = useState(false);
  const [retrievedAt, setRetrievedAt] = useState<string | null>(null);
  const [added, setAdded] = useState(0);

  const discover = async () => {
    setError(null);
    setLoading(true);
    try {
      const response = await api.discover(query.trim() || goal.trim());
      setResults(response.results);
      setCached(!!response.cached);
      setRetrievedAt(response.retrieved_at ?? null);
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
        <h2 className="font-display text-xl">Find Sources Automatically</h2>
        <p className="mt-1 text-sm text-inksoft">
          Automatic source discovery is currently unavailable. You can still add website links, paste information,
          or upload documents.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-line bg-card p-5 shadow-card">
      <h2 className="font-display text-xl">Find Sources Automatically</h2>
      <p className="mt-1 text-sm text-inksoft">
        Discover relevant websites using an available search provider. Results are <strong>suggested sources</strong> only —
        a search snippet is not verified evidence. Select the ones that look relevant, then add them; only then are
        they fetched (as <strong>successfully fetched</strong> or <strong>failed</strong> sources) and analyzed.
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
      {searched && results.length > 0 && cached && (
        <p className="mt-3 text-sm text-inksoft">
          Cached results — retrieved {retrievedAt ? new Date(retrievedAt).toLocaleString() : "earlier"}, not a fresh
          search. No provider quota was used for this search.
        </p>
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
                  <p className="text-xs font-semibold uppercase tracking-wide text-inksoft">Suggested source</p>
                  <a href={r.link} target="_blank" rel="noreferrer" className="text-sm font-semibold text-indigoaccent hover:underline">
                    {r.title}
                  </a>
                  <p className="text-xs text-inksoft">{r.domain ?? r.link}</p>
                  <p className="text-xs text-inksoft break-all">{r.link}</p>
                  {r.snippet && <p className="mt-1 text-sm">{r.snippet}</p>}
                </div>
              </li>
            ))}
          </ul>
          <button
            type="button"
            disabled={selected.size === 0}
            onClick={() => { onAdd([...selected]); setAdded(selected.size); setSelected(new Set()); }}
            className="mt-3 rounded-xl bg-indigoaccent px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            Add {selected.size} selected {selected.size === 1 ? "source" : "sources"} to investigation
          </button>
          {added > 0 && (
            <p className="mt-2 text-sm text-inksoft">
              Added {added} {added === 1 ? "source" : "sources"} — they now appear below in Step 3 as website links to
              fetch. A selected source only becomes analyzed evidence after a successful fetch.
            </p>
          )}
        </>
      )}
    </section>
  );
}
