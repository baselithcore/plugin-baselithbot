import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api, type AgentOS, type AgentStatus, type AgentSummary } from '../lib/api';
import { Button, Card, EmptyState, Icon, PageHeader } from '../components/ui';

const STATUS_TONE: Record<AgentStatus, string> = {
  online: 'text-status-success',
  enrolled: 'text-brand',
  offline: 'text-text-muted',
  revoked: 'text-sev-critical',
  disabled: 'text-accent-warn',
};

const OS_LABEL: Record<AgentOS, string> = {
  linux: 'Linux',
  macos: 'macOS',
  windows: 'Windows',
};

function relTime(iso: string | null): string {
  if (!iso) return 'never';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function FleetRow({ a }: { a: AgentSummary }) {
  return (
    <Link
      to={`/fleet/${a.agent_uuid}`}
      className="grid grid-cols-[2fr_1fr_1fr_1.4fr_1fr_0.8fr] items-center gap-3 border-b border-bg-line/50 px-5 py-3.5 transition-colors hover:bg-bg-hover/50"
    >
      <div className="min-w-0 truncate font-mono text-sm text-text-strong">
        {a.hostname ?? a.agent_uuid}
      </div>
      <div className="font-mono text-xs text-text-muted">
        {OS_LABEL[a.os]} <span className="opacity-60">/ {a.arch}</span>
      </div>
      <div className={`font-mono text-xs uppercase tracking-wider ${STATUS_TONE[a.status]}`}>
        {a.status}
      </div>
      <div className="font-mono text-xs text-text-muted">seen {relTime(a.last_seen_at)}</div>
      <div className="font-mono text-xs text-text-muted">{a.daemon_version ?? '—'}</div>
      <div className="text-right font-mono text-xs text-text-muted">
        {a.capabilities.length} caps
      </div>
    </Link>
  );
}

function EnrollmentTokenButton() {
  const qc = useQueryClient();
  const [issued, setIssued] = useState<string | null>(null);
  const mut = useMutation({
    mutationFn: () => api.createEnrollmentToken({ ttl_seconds: 86400 }),
    onSuccess: (data) => {
      setIssued(data.token);
      qc.invalidateQueries({ queryKey: ['fleet'] });
    },
  });
  return (
    <div className="flex items-center gap-2">
      <Button variant="primary" onClick={() => mut.mutate()} disabled={mut.isPending}>
        <Icon.Plus size={14} />
        New enrollment token
      </Button>
      {issued && (
        <code
          className="select-all rounded border border-bg-line bg-bg-elev px-2 py-1 font-mono text-xs"
          title="Copy this token now — it will not be shown again"
        >
          {issued}
        </code>
      )}
    </div>
  );
}

export function FleetList() {
  const [statusFilter, setStatusFilter] = useState<AgentStatus | undefined>();
  const [osFilter, setOsFilter] = useState<AgentOS | undefined>();

  const fleetQ = useQuery({
    queryKey: ['fleet', statusFilter, osFilter],
    queryFn: () =>
      api.listFleet({
        status_filter: statusFilter,
        os: osFilter,
        limit: 200,
      }),
    refetchInterval: 15_000,
  });

  const counts = useMemo(() => {
    const all = fleetQ.data ?? [];
    return {
      total: all.length,
      online: all.filter((a) => a.status === 'online').length,
      offline: all.filter((a) => a.status === 'offline').length,
      revoked: all.filter((a) => a.status === 'revoked').length,
    };
  }, [fleetQ.data]);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Fleet"
        description="Endpoint daemons enrolled in this tenant"
        actions={<EnrollmentTokenButton />}
      />

      <div className="grid grid-cols-4 gap-3">
        <StatCard label="Agents" value={counts.total} tone="text-text-strong" />
        <StatCard label="Online" value={counts.online} tone="text-status-success" />
        <StatCard label="Offline" value={counts.offline} tone="text-text-muted" />
        <StatCard label="Revoked" value={counts.revoked} tone="text-sev-critical" />
      </div>

      <Card>
        <div className="flex items-center gap-2 border-b border-bg-line px-5 py-3">
          <FilterChip
            label="status"
            value={statusFilter}
            options={['online', 'enrolled', 'offline', 'revoked', 'disabled']}
            onChange={(v) => setStatusFilter(v as AgentStatus | undefined)}
          />
          <FilterChip
            label="os"
            value={osFilter}
            options={['linux', 'macos', 'windows']}
            onChange={(v) => setOsFilter(v as AgentOS | undefined)}
          />
        </div>

        <div className="grid grid-cols-[2fr_1fr_1fr_1.4fr_1fr_0.8fr] gap-3 border-b border-bg-line px-5 py-2 font-mono text-xs uppercase tracking-wider text-text-muted">
          <span>host</span>
          <span>os</span>
          <span>status</span>
          <span>last seen</span>
          <span>version</span>
          <span className="text-right">caps</span>
        </div>

        {fleetQ.isLoading ? (
          <div className="px-5 py-8 text-center font-mono text-sm text-text-muted">
            loading fleet…
          </div>
        ) : fleetQ.data && fleetQ.data.length > 0 ? (
          fleetQ.data.map((a) => <FleetRow key={a.agent_uuid} a={a} />)
        ) : (
          <EmptyState
            icon={<Icon.Server size={28} />}
            title="No agents enrolled"
            description="Mint an enrollment token, run `baselith-redagent-daemon enroll --token …` on the target host."
          />
        )}
      </Card>
    </div>
  );
}

function StatCard({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <Card className="px-5 py-3">
      <div className="font-mono text-xs uppercase tracking-wider text-text-muted">{label}</div>
      <div className={`mt-1 font-mono text-3xl ${tone}`}>{value}</div>
    </Card>
  );
}

function FilterChip<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T | undefined;
  options: T[];
  onChange: (v: T | undefined) => void;
}) {
  const baseClass =
    'inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs font-mono transition-colors';
  const activeClass = 'bg-brand/10 text-brand border-brand/40';
  const idleClass = 'bg-bg-overlay text-text-secondary border-bg-line hover:text-text-strong';
  return (
    <div className="flex items-center gap-1">
      <span className="font-mono text-xs uppercase tracking-wider text-text-muted">{label}:</span>
      <button
        type="button"
        className={`${baseClass} ${value === undefined ? activeClass : idleClass}`}
        onClick={() => onChange(undefined)}
      >
        all
      </button>
      {options.map((o) => (
        <button
          key={o}
          type="button"
          className={`${baseClass} ${value === o ? activeClass : idleClass}`}
          onClick={() => onChange(value === o ? undefined : o)}
        >
          {o}
        </button>
      ))}
    </div>
  );
}
