import { useState } from 'react';
import { GlassPanel } from '../components/GlassPanel';
import { api } from '../lib/api';
import type { DocCitation } from '../lib/types';

/** Explore the same documentation index agents are grounded in over MCP. */
export function Docs() {
  const [query, setQuery] = useState('');
  const [hits, setHits] = useState<DocCitation[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function search() {
    setBusy(true);
    setError(null);
    try {
      setHits(await api.searchDocs(query));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <GlassPanel
      title="Framework documentation · MCP grounding"
      subtitle="The corpus agents consult to stay in-scope. Exposed as MCP tools too."
    >
      <div className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && search()}
          placeholder="Search the BaselithCore docs…"
          className="flex-1 rounded-xl border border-ink-600/60 bg-ink-900/60 px-4 py-2 text-sm text-slate-100 outline-none focus:border-iris/50"
        />
        <button
          onClick={search}
          disabled={busy || !query.trim()}
          className="rounded-lg bg-gradient-to-r from-iris to-cyan px-4 py-2 text-sm font-semibold text-ink-900 disabled:opacity-40"
        >
          {busy ? '…' : 'Search'}
        </button>
      </div>

      {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}

      <div className="mt-4 space-y-3">
        {hits.map((h) => (
          <div key={h.namespace} className="rounded-xl border border-ink-600/50 bg-ink-800/40 p-4">
            <div className="mb-1 flex items-center justify-between">
              <span className="font-mono text-xs text-cyan">{h.namespace}</span>
              <span className="text-[11px] text-slate-500">score {h.score.toFixed(1)}</span>
            </div>
            <p className="whitespace-pre-wrap text-xs text-slate-400">{h.snippet}</p>
          </div>
        ))}
        {!busy && hits.length === 0 && (
          <p className="text-sm text-slate-500">
            Try “plugin manifest integrity” or “orchestration loop budget”.
          </p>
        )}
      </div>
    </GlassPanel>
  );
}
