/**
 * Cross-community high-confidence edges (graphify "surprising connections").
 *
 * Rendered as a collapsible drawer in the corner of the graph page —
 * insight-density view that survives filter changes. Clicking an edge
 * pivots both endpoints into the EntitySidebar (via `onPivot`).
 */

import { Sparkles } from 'lucide-react';
import type { GraphData, SurprisingEdge } from '../../lib/api/graph';

interface SurprisingPanelProps {
  data: GraphData;
  onPivot: (entityId: string) => void;
}

export function SurprisingPanel({ data, onPivot }: SurprisingPanelProps) {
  const items = data.surprising.slice(0, 8);

  return (
    <section
      className="flex flex-col gap-2 rounded-2xl border border-[var(--color-border)] bg-canvas-raised p-4"
      aria-label="connessioni sorprendenti"
    >
      <header className="flex items-center gap-2">
        <Sparkles size={14} className="text-[var(--color-warning)]" aria-hidden />
        <h2 className="text-sm font-semibold text-ink">Connessioni sorprendenti</h2>
      </header>
      <p className="text-xs text-ink-muted">
        Archi ad alta confidence che attraversano community diverse — di solito i collegamenti
        più informativi del grafo.
      </p>
      {items.length === 0 ? (
        <div className="rounded-md bg-canvas px-3 py-2 text-xs text-ink-muted">
          Nessun arco sorprendente alla soglia corrente. Prova ad abbassare
          <code className="mx-1 rounded bg-canvas-raised px-1">GRAPH_CONFIDENCE_MIN</code>
          o ad estrarre più pagine.
        </div>
      ) : (
        <ul className="flex flex-col gap-1">
          {items.map((e) => (
            <li key={`${e.src}-${e.kind}-${e.dst}`}>
              <SurprisingItem edge={e} onPivot={onPivot} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

interface SurprisingItemProps {
  edge: SurprisingEdge;
  onPivot: (entityId: string) => void;
}

function SurprisingItem({ edge, onPivot }: SurprisingItemProps) {
  return (
    <div className="flex flex-col gap-1 rounded-md border border-[var(--color-border)] bg-canvas p-2">
      <div className="flex items-center gap-1.5 text-sm">
        <button
          type="button"
          className="text-ink hover:underline"
          onClick={() => onPivot(edge.src)}
        >
          {prettifyId(edge.src)}
        </button>
        <span className="rounded bg-canvas-raised px-1.5 py-0.5 font-mono text-xs text-ink-muted">
          {edge.kind}
        </span>
        <button
          type="button"
          className="text-ink hover:underline"
          onClick={() => onPivot(edge.dst)}
        >
          {prettifyId(edge.dst)}
        </button>
      </div>
      <div className="flex items-center justify-between text-xs text-ink-muted">
        <span>
          C{edge.src_community} ↔ C{edge.dst_community}
        </span>
        <span className="tabular-nums">conf {edge.confidence.toFixed(2)}</span>
      </div>
    </div>
  );
}

function prettifyId(id: string): string {
  const idx = id.indexOf(':');
  return idx >= 0 ? id.slice(idx + 1).replace(/-/g, ' ') : id;
}
