/**
 * Filter rail for the graph viz.
 *
 * Pure controlled component — owns no state, just renders the current
 * selections + emits change callbacks. Empty set = "no filter applied"
 * (all visible). Single source of truth lives in `GraphPage`.
 */

import { useMemo } from 'react';
import { Search } from 'lucide-react';
import type { GraphData } from '../../lib/api/graph';

interface GraphFiltersProps {
  data: GraphData;
  search: string;
  onSearchChange: (q: string) => void;
  visibleKinds: Set<string>;
  onToggleKind: (kind: string) => void;
  visibleCommunities: Set<number>;
  onToggleCommunity: (id: number) => void;
  confidenceMin: number;
  onConfidenceMinChange: (v: number) => void;
}

export function GraphFilters({
  data,
  search,
  onSearchChange,
  visibleKinds,
  onToggleKind,
  visibleCommunities,
  onToggleCommunity,
  confidenceMin,
  onConfidenceMinChange,
}: GraphFiltersProps) {
  const kinds = useMemo(() => {
    const counter = new Map<string, number>();
    for (const n of data.nodes) counter.set(n.kind, (counter.get(n.kind) ?? 0) + 1);
    return Array.from(counter.entries()).sort((a, b) => b[1] - a[1]);
  }, [data.nodes]);

  // Largest communities first (most informative when filtering).
  const topCommunities = useMemo(
    () => data.communities.slice().sort((a, b) => b.size - a.size).slice(0, 10),
    [data.communities]
  );

  const showAllKinds = visibleKinds.size === 0;
  const showAllCommunities = visibleCommunities.size === 0;

  return (
    <aside
      className="flex w-72 flex-col gap-5 overflow-y-auto rounded-2xl border border-[var(--color-border)] bg-canvas-raised p-4"
      aria-label="filtri grafo"
    >
      <header>
        <h2 className="text-sm font-semibold text-ink">Filtri</h2>
        <p className="text-xs text-ink-muted">Restringi visualizzazione.</p>
      </header>

      <section className="flex flex-col gap-2">
        <label htmlFor="graph-search" className="text-xs font-medium text-ink-muted">
          Cerca entità
        </label>
        <div className="relative">
          <Search
            className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-ink-muted"
            size={14}
            aria-hidden
          />
          <input
            id="graph-search"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="nome…"
            className="w-full rounded-lg border border-[var(--color-border)] bg-canvas py-1.5 pl-7 pr-2 text-sm text-ink outline-none focus:border-accent"
          />
        </div>
      </section>

      <section className="flex flex-col gap-2">
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium text-ink-muted">Tipi entità</span>
          {!showAllKinds && (
            <button
              type="button"
              className="text-accent hover:underline"
              onClick={() => kinds.forEach(([k]) => visibleKinds.has(k) && onToggleKind(k))}
            >
              reset
            </button>
          )}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {kinds.map(([kind, count]) => {
            const active = showAllKinds || visibleKinds.has(kind);
            return (
              <button
                key={kind}
                type="button"
                onClick={() => onToggleKind(kind)}
                className={
                  'rounded-full border px-2 py-0.5 text-xs transition-colors ' +
                  (active
                    ? 'border-accent bg-accent/10 text-ink'
                    : 'border-[var(--color-border)] bg-canvas text-ink-muted opacity-60')
                }
                aria-pressed={active}
              >
                {kind} <span className="text-ink-muted">{count}</span>
              </button>
            );
          })}
        </div>
      </section>

      <section className="flex flex-col gap-2">
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium text-ink-muted">Community (top 10)</span>
          {!showAllCommunities && (
            <button
              type="button"
              className="text-accent hover:underline"
              onClick={() =>
                topCommunities.forEach((c) =>
                  visibleCommunities.has(c.id) && onToggleCommunity(c.id)
                )
              }
            >
              reset
            </button>
          )}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {topCommunities.map((c) => {
            const active = showAllCommunities || visibleCommunities.has(c.id);
            return (
              <button
                key={c.id}
                type="button"
                onClick={() => onToggleCommunity(c.id)}
                className={
                  'rounded-full border px-2 py-0.5 text-xs transition-colors ' +
                  (active
                    ? 'border-accent bg-accent/10 text-ink'
                    : 'border-[var(--color-border)] bg-canvas text-ink-muted opacity-60')
                }
                aria-pressed={active}
                title={`cohesion ${c.cohesion.toFixed(2)}`}
              >
                C{c.id} <span className="text-ink-muted">{c.size}</span>
              </button>
            );
          })}
        </div>
      </section>

      <section className="flex flex-col gap-2">
        <label htmlFor="graph-conf" className="flex items-center justify-between text-xs">
          <span className="font-medium text-ink-muted">Min confidence</span>
          <span className="tabular-nums text-ink">{confidenceMin.toFixed(2)}</span>
        </label>
        <input
          id="graph-conf"
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={confidenceMin}
          onChange={(e) => onConfidenceMinChange(Number(e.target.value))}
          className="w-full accent-accent"
        />
      </section>

      <footer className="mt-auto rounded-lg bg-canvas px-3 py-2 text-xs text-ink-muted">
        <div>Nodi: <span className="text-ink">{data.stats.node_count}</span></div>
        <div>Archi: <span className="text-ink">{data.stats.edge_count}</span></div>
        <div>Community: <span className="text-ink">{data.stats.community_count}</span></div>
      </footer>
    </aside>
  );
}
