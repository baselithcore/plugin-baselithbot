import { MiniGraph } from '../../MiniGraph';

export function GraphPanel({
  findingId,
  data,
  isLoading,
  error,
  partial = false,
}: {
  findingId: string;
  data: import('../../../../lib/api').AttackSurfaceResp | undefined;
  isLoading: boolean;
  error: Error | null;
  partial?: boolean;
}) {
  if (partial) {
    return (
      <div className="rounded border border-bg-line bg-bg-overlay/40 p-4 text-sm text-text-secondary">
        <div className="font-mono text-2xs uppercase tracking-wider text-text-muted">
          Subgraph unavailable
        </div>
        <p className="mt-2">
          Finding reconstructed from the attack-surface graph; subgraph drilldown is disabled. Open
          the full graph view from the navbar to inspect neighborhood.
        </p>
      </div>
    );
  }
  if (isLoading) {
    return (
      <div className="grid place-items-center py-16 text-sm text-text-muted">Loading subgraph…</div>
    );
  }
  if (error) {
    return (
      <div className="rounded border border-sev-critical/40 bg-sev-critical/10 p-3 text-sm text-sev-critical">
        {String(error)}
      </div>
    );
  }
  if (!data || data.nodes.length === 0) {
    return (
      <div className="grid place-items-center py-16 text-sm text-text-muted">
        No graph relations recorded for this finding yet.
      </div>
    );
  }
  return (
    <div className="flex h-full flex-col gap-2">
      <p className="px-2 text-2xs font-mono uppercase tracking-wider text-text-muted">
        2-hop neighborhood · {data.nodes.length} nodes · {data.edges.length} edges
      </p>
      <div className="min-h-0 flex-1">
        <MiniGraph data={data} fill highlightId={findingId} />
      </div>
    </div>
  );
}
