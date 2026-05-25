/**
 * Detail panel for the currently-selected entity.
 *
 * Renders metadata + lazy-loaded neighbor list (1-hop). Clicking a
 * neighbor delegates back via `onSelectEntity` so the canvas can recenter
 * + the panel can refresh.
 */

import { useEffect, useState } from 'react';
import { ChevronRight, ExternalLink, X } from 'lucide-react';
import {
  getEntity,
  getNeighbors,
  type EntityRecord,
  type GraphNode,
  type NeighborsResponse,
  GraphUnavailableError,
} from '../../lib/api/graph';

interface EntitySidebarProps {
  node: GraphNode | null;
  onClose: () => void;
  onSelectEntity: (id: string) => void;
}

export function EntitySidebar({ node, onClose, onSelectEntity }: EntitySidebarProps) {
  const [entity, setEntity] = useState<EntityRecord | null>(null);
  const [neighbors, setNeighbors] = useState<NeighborsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!node) {
      setEntity(null);
      setNeighbors(null);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([getEntity(node.id), getNeighbors(node.id, { hops: 1, limit: 25 })])
      .then(([e, nbrs]) => {
        if (cancelled) return;
        setEntity(e);
        setNeighbors(nbrs);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof GraphUnavailableError) {
          setError('Grafo non disponibile.');
        } else {
          setError(err instanceof Error ? err.message : 'Errore caricamento dettagli.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [node]);

  if (!node) return null;

  return (
    <aside
      className="flex w-80 flex-col gap-3 overflow-y-auto rounded-2xl border border-[var(--color-border)] bg-canvas-raised p-4"
      aria-label="dettaglio entità"
    >
      <header className="flex items-start justify-between gap-2">
        <div>
          <div className="text-xs font-mono text-ink-muted">{node.kind}</div>
          <h2 className="text-base font-semibold text-ink">{entity?.name ?? node.name}</h2>
          <div className="mt-1 flex flex-wrap gap-1 text-xs text-ink-muted">
            <span>PR {node.pagerank.toFixed(4)}</span>
            <span>·</span>
            <span>community {node.community}</span>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="chiudi dettaglio"
          className="rounded-md p-1 text-ink-muted hover:bg-canvas hover:text-ink"
        >
          <X size={16} />
        </button>
      </header>

      {entity?.aliases && entity.aliases.length > 0 && (
        <section className="flex flex-col gap-1">
          <div className="text-xs font-medium text-ink-muted">Alias</div>
          <div className="flex flex-wrap gap-1">
            {entity.aliases.map((a) => (
              <span
                key={a}
                className="rounded-full border border-[var(--color-border)] bg-canvas px-2 py-0.5 text-xs text-ink"
              >
                {a}
              </span>
            ))}
          </div>
        </section>
      )}

      <section className="flex flex-col gap-1">
        <div className="text-xs font-medium text-ink-muted">ID</div>
        <code className="select-all break-all rounded-md bg-canvas px-2 py-1 text-xs text-ink">
          {node.id}
        </code>
      </section>

      <section className="flex flex-col gap-2">
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium text-ink-muted">Vicini (1-hop)</span>
          {neighbors && <span className="text-ink-muted">{neighbors.count}</span>}
        </div>
        {loading && (
          <div className="rounded-md bg-canvas px-3 py-2 text-xs text-ink-muted">Carico…</div>
        )}
        {error && (
          <div className="rounded-md bg-canvas px-3 py-2 text-xs text-[var(--color-danger)]">{error}</div>
        )}
        {!loading && !error && neighbors && neighbors.results.length === 0 && (
          <div className="rounded-md bg-canvas px-3 py-2 text-xs text-ink-muted">
            Nessun vicino con la confidence corrente.
          </div>
        )}
        <ul className="flex flex-col gap-1">
          {neighbors?.results.map((n) => (
            <li key={n.id}>
              <button
                type="button"
                onClick={() => onSelectEntity(n.id)}
                className="flex w-full items-center justify-between gap-2 rounded-md border border-[var(--color-border)] bg-canvas px-2 py-1.5 text-left text-sm text-ink hover:border-accent"
              >
                <span className="flex flex-col">
                  <span>{n.name}</span>
                  <span className="text-xs text-ink-muted">{n.kind}</span>
                </span>
                <ChevronRight size={14} className="text-ink-muted" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      </section>

      {node.id && (
        <a
          href={`#${node.id}`}
          className="mt-auto inline-flex items-center gap-1 text-xs text-accent hover:underline"
        >
          <ExternalLink size={12} aria-hidden />
          Vedi pagina wiki collegata
        </a>
      )}
    </aside>
  );
}
