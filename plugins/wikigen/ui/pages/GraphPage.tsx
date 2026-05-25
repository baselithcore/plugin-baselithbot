/**
 * Knowledge-graph exploration page (graphify PR3).
 *
 * Three-column layout:
 *   ┌────────────┬──────────────────────────────┬────────────┐
 *   │  Filters   │         GraphCanvas          │  Detail    │
 *   │            │                              │  + Surpr.  │
 *   └────────────┴──────────────────────────────┴────────────┘
 *
 * Owns filter state + active selection. Data is fetched once on mount;
 * filter changes are local (no re-fetch). Confidence slider is wired
 * into the canvas through class-based dimming, not a remount.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, ArrowLeft, RefreshCcw } from 'lucide-react';
import { navigate } from '../hooks/useLocation';
import {
  getData,
  GraphUnavailableError,
  type GraphData,
  type GraphNode,
} from '../lib/api/graph';
import { GraphCanvas, type ViewMode } from '../components/graph/GraphCanvas';
import { GraphEmptyState } from '../components/graph/GraphEmptyState';
import { GraphFilters } from '../components/graph/GraphFilters';
import { EntitySidebar } from '../components/graph/EntitySidebar';
import { SurprisingPanel } from '../components/graph/SurprisingPanel';
import { Hint } from '../components/ui';

export function GraphPage() {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  const [search, setSearch] = useState('');
  const [visibleKinds, setVisibleKinds] = useState<Set<string>>(new Set());
  const [visibleCommunities, setVisibleCommunities] = useState<Set<number>>(new Set());
  const [confidenceMin, setConfidenceMin] = useState(0.5);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>(() => readPersistedViewMode());

  useEffect(() => {
    try {
      window.localStorage.setItem(VIEW_MODE_STORAGE_KEY, viewMode);
    } catch {
      // ignore storage errors (private mode / quota)
    }
  }, [viewMode]);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    setUnavailable(false);
    getData({ confidence_min: 0, max_nodes: 500 })
      .then((d) => {
        if (!d.enabled) {
          setUnavailable(true);
          setData(null);
          return;
        }
        setData(d);
      })
      .catch((err) => {
        if (err instanceof GraphUnavailableError) {
          setUnavailable(true);
        } else {
          setError(err instanceof Error ? err.message : 'Errore caricamento grafo.');
        }
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const selectedNode = useMemo<GraphNode | null>(() => {
    if (!data || !selectedId) return null;
    return data.nodes.find((n) => n.id === selectedId) ?? null;
  }, [data, selectedId]);

  const handleToggleKind = useCallback((kind: string) => {
    setVisibleKinds((prev) => {
      const next = new Set(prev);
      if (next.has(kind)) next.delete(kind);
      else next.add(kind);
      return next;
    });
  }, []);

  const handleToggleCommunity = useCallback((id: number) => {
    setVisibleCommunities((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleSelectNode = useCallback((node: GraphNode | null) => {
    setSelectedId(node?.id ?? null);
  }, []);

  return (
    <div className="flex h-screen w-screen flex-col bg-canvas text-ink">
      <header className="flex items-center justify-between gap-3 border-b border-[var(--color-border)] px-4 py-2">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm text-ink-muted hover:bg-canvas-raised hover:text-ink"
            aria-label="Back to chat"
          >
            <ArrowLeft size={14} aria-hidden />
            Chat
          </button>
          <span className="text-ink-muted">·</span>
          <h1 className="text-sm font-semibold">Knowledge Graph</h1>
          {data && (
            <span className="text-xs text-ink-muted">
              {data.stats.node_count} entità · {data.stats.edge_count} relazioni ·{' '}
              {data.stats.community_count} community
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="inline-flex items-center gap-1 rounded-md border border-[var(--color-border)] px-2 py-1 text-xs text-ink-muted hover:bg-canvas-raised hover:text-ink disabled:opacity-50"
        >
          <RefreshCcw size={12} aria-hidden />
          Ricarica
        </button>
      </header>

      <main className="flex flex-1 gap-3 overflow-hidden p-3">
        {loading && <CenterBanner kind="info" text="Caricamento grafo in corso…" />}
        {!loading && unavailable && (
          <CenterBanner
            kind="warning"
            text="Grafo non disponibile. Abilita GRAPH_DB_ENABLED + avvia FalkorDB (`docker compose --profile graph up -d`)."
          />
        )}
        {!loading && error && <CenterBanner kind="error" text={error} />}
        {!loading && data && data.nodes.length === 0 && (
          <GraphEmptyState onReload={load} />
        )}
        {!loading && data && data.nodes.length > 0 && (
          <>
            <GraphFilters
              data={data}
              search={search}
              onSearchChange={setSearch}
              visibleKinds={visibleKinds}
              onToggleKind={handleToggleKind}
              visibleCommunities={visibleCommunities}
              onToggleCommunity={handleToggleCommunity}
              confidenceMin={confidenceMin}
              onConfidenceMinChange={setConfidenceMin}
            />

            <section className="flex flex-1 min-w-0 flex-col gap-2">
              <Hint
                id="graph.first_visit"
                tone="info"
                title="Esplora il knowledge graph"
              >
                <span className="block">
                  Ogni nodo è un'entità estratta dalle pagine; gli archi sono
                  relazioni tipate. Colore = community, dimensione = PageRank,
                  spessore arco = confidence.
                </span>
                <span className="mt-1 block text-[10.5px] text-ink-subtle">
                  Toggle in alto a destra: 2D force / 3D orbit / Layout
                  deterministico. Hover sui nodi per vedere il vicinato (auto-off
                  sui grafi densi). Click per il dettaglio · filtri a sinistra ·
                  «connessioni sorprendenti» a destra finché non selezioni un nodo.
                </span>
              </Hint>
              <div className="min-h-0 flex-1">
                <GraphCanvas
                  data={data}
                  visibleKinds={visibleKinds}
                  visibleCommunities={visibleCommunities}
                  confidenceMin={confidenceMin}
                  search={search}
                  onSelectNode={handleSelectNode}
                  selectedNodeId={selectedId}
                  viewMode={viewMode}
                  onViewModeChange={setViewMode}
                />
              </div>
            </section>

            <div className="flex w-80 flex-col gap-3 overflow-hidden">
              {selectedNode ? (
                <EntitySidebar
                  node={selectedNode}
                  onClose={() => setSelectedId(null)}
                  onSelectEntity={setSelectedId}
                />
              ) : (
                <SurprisingPanel data={data} onPivot={setSelectedId} />
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}

const VIEW_MODE_STORAGE_KEY = 'graph.viewMode';

function readPersistedViewMode(): ViewMode {
  if (typeof window === 'undefined') return '2d';
  try {
    const v = window.localStorage.getItem(VIEW_MODE_STORAGE_KEY);
    if (v === '2d' || v === '3d' || v === 'cose') return v;
  } catch {
    // ignore
  }
  return '2d';
}

interface CenterBannerProps {
  kind: 'info' | 'warning' | 'error';
  text: string;
}

function CenterBanner({ kind, text }: CenterBannerProps) {
  const colour =
    kind === 'error'
      ? 'border-[var(--color-danger)]/40 bg-[var(--color-danger)]/10 text-[var(--color-danger)]'
      : kind === 'warning'
        ? 'border-[var(--color-warning)]/40 bg-[var(--color-warning)]/10 text-[var(--color-warning)]'
        : 'border-[var(--color-border)] bg-canvas-raised text-ink-muted';
  return (
    <div
      className={
        'm-auto flex max-w-md items-center gap-2 rounded-2xl border px-4 py-3 text-sm ' +
        colour
      }
      role="status"
    >
      {kind !== 'info' && <AlertTriangle size={16} aria-hidden />}
      <span>{text}</span>
    </div>
  );
}
