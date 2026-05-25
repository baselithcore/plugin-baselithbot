import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../../lib/api';
import { Card, EmptyState, Icon, MiniGraph } from '../../components/ui';

export function SurfaceTab({ targetValue }: { targetValue: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['attack-surface', targetValue],
    queryFn: () => api.getAttackSurface(targetValue),
    enabled: Boolean(targetValue),
    refetchInterval: 30_000,
  });

  return (
    <Card
      title="Attack surface"
      subtitle="Vulnerability graph scoped to this target"
      action={
        <Link
          to={`/graph?target=${encodeURIComponent(targetValue)}`}
          className="ra-btn ra-btn-ghost ra-btn-sm"
        >
          <Icon.Graph size={12} />
          Open full graph
        </Link>
      }
      padded={false}
    >
      <div className="px-4 py-4">
        {isLoading ? (
          <div className="grid place-items-center py-16 text-sm text-text-muted">
            Loading surface…
          </div>
        ) : error ? (
          <div className="rounded border border-sev-critical/40 bg-sev-critical/10 p-3 text-sm text-sev-critical">
            {String(error)}
          </div>
        ) : !data || data.nodes.length === 0 ? (
          <EmptyState
            compact
            icon={<Icon.Graph size={20} />}
            title="No graph yet"
            description="Run a scan to populate the attack surface."
          />
        ) : (
          <>
            <p className="mb-2 text-2xs font-mono uppercase tracking-wider text-text-muted">
              {data.nodes.length} nodes · {data.edges.length} edges · click a vulnerability to drill
              in
            </p>
            <MiniGraph data={data} height={520} />
          </>
        )}
      </div>
    </Card>
  );
}
