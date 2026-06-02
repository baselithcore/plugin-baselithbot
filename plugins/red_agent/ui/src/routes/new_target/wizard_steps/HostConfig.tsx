import { useQuery } from '@tanstack/react-query';
import { api, type AgentSummary } from '../../../lib/api';
import { Card, Icon } from '../../../components/ui';
import { Field } from './_shared';

export function HostConfig({
  agentUuid,
  setAgentUuid,
}: {
  agentUuid: string;
  setAgentUuid: (v: string) => void;
}) {
  // Pull the enrolled fleet so the operator can pick which daemon
  // executes scans for this target. We deliberately list every status
  // (including "offline") so a temporarily-disconnected host can still
  // be bound — the executor queues commands until the daemon
  // reconnects via its persistent gRPC stream.
  const fleet = useQuery({
    queryKey: ['fleet', 'host-target-picker'],
    queryFn: () => api.listFleet({ limit: 500 }),
    staleTime: 30_000,
  });

  const agents: AgentSummary[] = fleet.data ?? [];
  const filtered = agents.filter((a) => a.status !== 'revoked');

  return (
    <Card
      title="Host target"
      subtitle="Bind this target to an enrolled Red Agent daemon — or run the in-process posture scanner against the orchestrator host itself."
    >
      <div className="space-y-4">
        <div className="rounded-md border border-brand/30 bg-brand/5 p-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h4 className="font-display text-sm font-medium text-text-primary">
                Audit this orchestrator
              </h4>
              <p className="mt-1 text-xs text-text-muted">
                Run the CIS-aligned <span className="font-mono">self_posture</span> scanner against
                the host running the backend. Pure-Python, no daemon, no network.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setAgentUuid('local')}
              className={`rounded-md border px-3 py-1.5 text-2xs font-mono uppercase tracking-wider transition-colors ${
                agentUuid === 'local'
                  ? 'border-brand/60 bg-brand/15 text-brand ring-1 ring-brand/30'
                  : 'border-bg-line bg-bg-elevated text-text-secondary hover:border-brand/40'
              }`}
            >
              {agentUuid === 'local' ? 'selected' : 'use this host'}
            </button>
          </div>
        </div>
        {fleet.isLoading && <p className="text-xs text-text-muted">Loading enrolled fleet…</p>}
        {fleet.isError && (
          <p className="text-xs text-sev-critical">
            Failed to load fleet — check that the Red Agent backend is reachable.
          </p>
        )}
        {!fleet.isLoading && !fleet.isError && filtered.length === 0 && (
          <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-300">
            <Icon.Shield size={12} className="mr-1.5 inline" />
            No enrolled daemons. Mint an enrollment token from the{' '}
            <a className="font-mono underline" href="/fleet">
              Fleet
            </a>{' '}
            tab and run{' '}
            <span className="font-mono">baselith-redagent-daemon enroll --token &lt;token&gt;</span>{' '}
            on the host.
          </div>
        )}
        {filtered.length > 0 && (
          <div>
            <label className="mb-1.5 block text-2xs font-mono uppercase tracking-wider text-text-muted">
              Enrolled daemon
            </label>
            <div className="grid gap-2">
              {filtered.map((a) => {
                const sel = agentUuid === a.agent_uuid;
                const stale = a.status === 'offline';
                return (
                  <button
                    key={a.agent_uuid}
                    type="button"
                    onClick={() => setAgentUuid(a.agent_uuid)}
                    className={`flex items-center justify-between gap-3 rounded-md border bg-bg-elevated px-3 py-2 text-left transition-colors ${
                      sel
                        ? 'border-brand/60 ring-1 ring-brand/30'
                        : 'border-bg-line hover:border-bg-line-strong'
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <Icon.Server size={14} className="text-amber-300" />
                        <span className="truncate font-display text-sm font-medium text-text-primary">
                          {a.hostname || a.agent_uuid}
                        </span>
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-2 font-mono text-2xs text-text-muted">
                        <span>{a.os}</span>
                        <span>·</span>
                        <span>{a.arch}</span>
                        {a.daemon_version && (
                          <>
                            <span>·</span>
                            <span>v{a.daemon_version}</span>
                          </>
                        )}
                        <span>·</span>
                        <span>{a.agent_uuid.slice(0, 8)}</span>
                      </div>
                    </div>
                    <span
                      className={`rounded px-1.5 py-0.5 text-2xs font-mono uppercase tracking-wider ring-1 ${
                        a.status === 'online'
                          ? 'bg-status-success/10 text-status-success ring-status-success/30'
                          : stale
                            ? 'bg-amber-500/10 text-amber-300 ring-amber-500/30'
                            : 'bg-bg-line/40 text-text-muted ring-bg-line'
                      }`}
                    >
                      {a.status}
                    </span>
                    {sel && <Icon.Check size={14} className="text-brand" />}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <Field
          label="Agent UUID (or paste manually)"
          hint="Useful when registering a target ahead of the daemon's first connect."
        >
          <input
            value={agentUuid}
            onChange={(e) => setAgentUuid(e.target.value.trim())}
            placeholder="00000000-0000-0000-0000-000000000000"
            className="ra-input font-mono"
          />
        </Field>

        <div className="rounded-md border border-accent-warn/30 bg-accent-warn/5 p-3 text-xs text-accent-warn">
          <Icon.Shield size={12} className="mr-1.5 inline" />
          Scans on host targets run inside the daemon's sandbox (landlock on linux, sandbox-exec on
          macOS) and are gated by the active policy bundle.
        </div>
      </div>
    </Card>
  );
}
