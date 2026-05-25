import { useQuery } from '@tanstack/react-query';
import { api, type AgentSummary, type ScanIntensity, type TargetKind } from '../../lib/api';
import { Card, Chip, Icon } from '../../components/ui';
import { KIND_META, KIND_ORDER } from '../../lib/targets';
import {
  SCANNERS_BY_INTENSITY as REGISTRY_SCANNERS_BY_INTENSITY,
  scannersForTargetKind,
} from '../../lib/scanners';

export const SCANNERS_BY_INTENSITY: Record<ScanIntensity, string[]> =
  REGISTRY_SCANNERS_BY_INTENSITY;

export const CLOUD_PROVIDERS = [
  { id: 'aws', label: 'AWS', accountField: 'Account ID', credField: 'IAM Role ARN' },
  { id: 'gcp', label: 'GCP', accountField: 'Project ID', credField: 'Service Account email' },
  {
    id: 'azure',
    label: 'Azure',
    accountField: 'Subscription ID',
    credField: 'App Registration ID',
  },
] as const;

export type CloudProvider = (typeof CLOUD_PROVIDERS)[number]['id'];

export function KindIcon({ k, size = 18 }: { k: TargetKind; size?: number }) {
  switch (k) {
    case 'web':
      return <Icon.Globe size={size} />;
    case 'cloud':
      return <Icon.Cloud size={size} />;
    case 'network':
      return <Icon.Network size={size} />;
    case 'host':
      return <Icon.Server size={size} />;
    case 'repo':
      return <Icon.Folder size={size} />;
    case 'binary':
      return <Icon.Bug size={size} />;
  }
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-2xs font-mono uppercase tracking-wider text-text-muted">
        {label}
      </label>
      {children}
      {hint && <p className="mt-1 text-xs text-text-muted">{hint}</p>}
    </div>
  );
}

export function ReviewRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div>
      <dt className="text-2xs font-mono uppercase tracking-wider text-text-muted">{label}</dt>
      <dd className={`mt-1 text-sm text-text-primary ${mono ? 'font-mono' : ''}`}>{value}</dd>
    </div>
  );
}

export function KindStep({
  kind,
  setKind,
}: {
  kind: TargetKind | null;
  setKind: (k: TargetKind) => void;
}) {
  return (
    <Card title="What kind of target?" subtitle="Pick the entity you want to assess">
      <div className="grid gap-3 sm:grid-cols-2">
        {KIND_ORDER.map((k) => {
          const meta = KIND_META[k];
          const sel = kind === k;
          const disabled = !!meta.comingSoon;
          return (
            <button
              key={k}
              type="button"
              disabled={disabled}
              onClick={() => !disabled && setKind(k)}
              className={`relative flex items-start gap-3 rounded-lg border bg-gradient-to-br p-4 text-left transition-all ${
                sel
                  ? 'border-brand/60 ring-1 ring-brand/40'
                  : disabled
                    ? 'border-bg-line opacity-60 cursor-not-allowed'
                    : 'border-bg-line hover:border-bg-line-strong'
              } ${meta.accent}`}
            >
              <div className="grid h-10 w-10 place-items-center rounded-md bg-bg-elevated/80 ring-1 ring-current/20">
                <KindIcon k={k} size={18} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="font-display text-sm font-medium text-text-primary">
                  {meta.label}
                </div>
                <p className="mt-1 text-xs text-text-muted">{meta.description}</p>
                <p className="mt-2 font-mono text-2xs text-text-subtle">{meta.hint}</p>
              </div>
              {meta.comingSoon && (
                <span className="absolute right-3 top-3 rounded bg-amber-500/10 px-1.5 py-0.5 text-2xs font-mono uppercase tracking-wider text-amber-300 ring-1 ring-amber-500/20">
                  coming soon
                </span>
              )}
              {sel && (
                <span className="absolute right-3 top-3 grid h-5 w-5 place-items-center rounded-full bg-brand/20 text-brand ring-1 ring-brand/40">
                  <Icon.Check size={11} />
                </span>
              )}
            </button>
          );
        })}
      </div>
    </Card>
  );
}

export type IdentityStepProps = {
  name: string;
  setName: (v: string) => void;
  environment: string;
  setEnvironment: (v: string) => void;
  owner: string;
  setOwner: (v: string) => void;
  tags: string;
  setTags: (v: string) => void;
  description: string;
  setDescription: (v: string) => void;
};

export function IdentityStep(p: IdentityStepProps) {
  return (
    <Card title="Identity & ownership" subtitle="Help your team find this later">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Display name">
          <input
            value={p.name}
            onChange={(e) => p.setName(e.target.value)}
            placeholder="Production API gateway"
            className="ra-input"
          />
        </Field>
        <Field label="Environment">
          <select
            value={p.environment}
            onChange={(e) => p.setEnvironment(e.target.value)}
            className="ra-select"
          >
            <option value="production">production</option>
            <option value="staging">staging</option>
            <option value="dev">dev</option>
            <option value="qa">qa</option>
          </select>
        </Field>
        <Field label="Owner team / email">
          <input
            value={p.owner}
            onChange={(e) => p.setOwner(e.target.value)}
            placeholder="platform-security@acme.com"
            className="ra-input"
          />
        </Field>
        <Field label="Tags (comma-separated)">
          <input
            value={p.tags}
            onChange={(e) => p.setTags(e.target.value)}
            placeholder="pci, public, tier-1"
            className="ra-input"
          />
        </Field>
        <div className="sm:col-span-2">
          <Field label="Description (optional)">
            <textarea
              value={p.description}
              onChange={(e) => p.setDescription(e.target.value)}
              placeholder="What is this target? Any context reviewers should know."
              rows={3}
              className="ra-input min-h-[88px] resize-y"
            />
          </Field>
        </div>
      </div>
    </Card>
  );
}

export type ConfigStepProps = {
  kind: TargetKind | null;
  webUrl: string;
  setWebUrl: (v: string) => void;
  netRange: string;
  setNetRange: (v: string) => void;
  cloudProvider: CloudProvider;
  setCloudProvider: (v: CloudProvider) => void;
  cloudAccountId: string;
  setCloudAccountId: (v: string) => void;
  cloudCredential: string;
  setCloudCredential: (v: string) => void;
  cloudRegion: string;
  setCloudRegion: (v: string) => void;
  hostAgentUuid: string;
  setHostAgentUuid: (v: string) => void;
  repoLocation: string;
  setRepoLocation: (v: string) => void;
  allowInternal: boolean;
  setAllowInternal: (v: boolean) => void;
};

export function ConfigStep(p: ConfigStepProps) {
  if (p.kind === 'web') {
    const isLocal = /^https?:\/\/(localhost|127\.0\.0\.1|::1|0\.0\.0\.0)(:|\/|$)/i.test(p.webUrl);
    return (
      <Card title="Web target" subtitle="URL or hostname of the application">
        <Field label="URL">
          <input
            value={p.webUrl}
            onChange={(e) => p.setWebUrl(e.target.value)}
            placeholder="https://api.example.com"
            className="ra-input"
          />
        </Field>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span className="text-2xs font-mono uppercase tracking-wider text-text-muted">
            Quick presets
          </span>
          <button
            type="button"
            onClick={() => {
              p.setWebUrl('http://localhost:8000');
              p.setAllowInternal(true);
            }}
            className="rounded border border-bg-line px-2 py-0.5 text-2xs font-mono text-text-secondary hover:border-brand/50 hover:text-brand"
          >
            this machine (localhost:8000)
          </button>
          <button
            type="button"
            onClick={() => {
              p.setWebUrl('http://127.0.0.1');
              p.setAllowInternal(true);
            }}
            className="rounded border border-bg-line px-2 py-0.5 text-2xs font-mono text-text-secondary hover:border-brand/50 hover:text-brand"
          >
            127.0.0.1
          </button>
        </div>
        {isLocal && (
          <label className="mt-3 flex cursor-pointer items-start gap-2 rounded-md border border-accent-warn/30 bg-accent-warn/5 p-3 text-xs text-accent-warn">
            <input
              type="checkbox"
              checked={p.allowInternal}
              onChange={(e) => p.setAllowInternal(e.target.checked)}
              className="mt-0.5 accent-brand"
            />
            <span>
              <strong className="font-display">Allow internal target</strong> — bypass SSRF
              guardrail for this loopback/private host. Required to scan the machine running the
              orchestrator. Only enable in trusted environments.
            </span>
          </label>
        )}
        {!isLocal && (
          <p className="mt-2 text-xs text-text-muted">
            Internal/loopback hosts are blocked by guardrails unless explicitly allow-listed in
            scope policy.
          </p>
        )}
      </Card>
    );
  }
  if (p.kind === 'network') {
    return (
      <Card title="Network target" subtitle="IP address or CIDR range">
        <Field label="Range">
          <input
            value={p.netRange}
            onChange={(e) => p.setNetRange(e.target.value)}
            placeholder="10.0.0.0/24"
            className="ra-input"
          />
        </Field>
      </Card>
    );
  }
  if (p.kind === 'host') {
    return <HostConfig agentUuid={p.hostAgentUuid} setAgentUuid={p.setHostAgentUuid} />;
  }
  if (p.kind === 'repo') {
    return (
      <Card
        title="Repository target"
        subtitle="Local filesystem path or git remote — scanned by SAST/SCA/secret/IaC adapters"
      >
        <Field
          label="Location"
          hint="Absolute path (e.g. /Users/me/dev/myrepo) or git URL (https/ssh). Path must be readable by the orchestrator process."
        >
          <input
            value={p.repoLocation}
            onChange={(e) => p.setRepoLocation(e.target.value)}
            placeholder="/path/to/repo or git@github.com:org/repo.git"
            className="ra-input font-mono"
          />
        </Field>
      </Card>
    );
  }
  if (p.kind === 'cloud') {
    const sel = CLOUD_PROVIDERS.find((x) => x.id === p.cloudProvider)!;
    return (
      <Card
        title="Cloud account"
        subtitle="Read-only role assumed by the cloud-context plugin (no credentials stored here)"
      >
        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-2xs font-mono uppercase tracking-wider text-text-muted">
              Provider
            </label>
            <div className="grid gap-2 sm:grid-cols-3">
              {CLOUD_PROVIDERS.map((prov) => {
                const active = p.cloudProvider === prov.id;
                return (
                  <button
                    key={prov.id}
                    type="button"
                    onClick={() => p.setCloudProvider(prov.id)}
                    className={`flex items-center gap-2 rounded-md border bg-bg-elevated p-3 text-left transition-colors ${
                      active
                        ? 'border-brand/60 ring-1 ring-brand/30'
                        : 'border-bg-line hover:border-bg-line-strong'
                    }`}
                  >
                    <Icon.Cloud size={16} className="text-violet-300" />
                    <span className="font-display text-sm font-medium text-text-primary">
                      {prov.label}
                    </span>
                    {active && <Icon.Check size={14} className="ml-auto text-brand" />}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={sel.accountField}>
              <input
                value={p.cloudAccountId}
                onChange={(e) => p.setCloudAccountId(e.target.value)}
                placeholder="123456789012"
                className="ra-input"
              />
            </Field>
            <Field label={sel.credField}>
              <input
                value={p.cloudCredential}
                onChange={(e) => p.setCloudCredential(e.target.value)}
                placeholder="arn:aws:iam::…:role/RedAgentReadOnly"
                className="ra-input"
              />
            </Field>
            <Field label="Default region">
              <input
                value={p.cloudRegion}
                onChange={(e) => p.setCloudRegion(e.target.value)}
                className="ra-input"
              />
            </Field>
          </div>
          <div className="rounded-md border border-accent-warn/30 bg-accent-warn/5 p-3 text-xs text-accent-warn">
            <Icon.Shield size={12} className="mr-1.5 inline" />
            Credentials are referenced — not stored — in the Red Agent. The cloud-context plugin
            assumes the role at scan time.
          </div>
        </div>
      </Card>
    );
  }
  return null;
}

function HostConfig({
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

export type ProfileStepProps = {
  kind: TargetKind | null;
  intensity: ScanIntensity;
  setIntensity: (v: ScanIntensity) => void;
  scanners: string[];
  setScanners: (cb: (cur: string[]) => string[]) => void;
  scheduleCron: string;
  setScheduleCron: (v: string) => void;
  resetScannersForIntensity: (i: ScanIntensity) => void;
};

export function ProfileStep(p: ProfileStepProps) {
  return (
    <Card title="Scan profile" subtitle="Defaults applied to every run against this target">
      <div className="space-y-5">
        <div>
          <label className="mb-2 block text-2xs font-mono uppercase tracking-wider text-text-muted">
            Default intensity
          </label>
          <div className="grid gap-2 sm:grid-cols-3">
            {(['passive', 'active', 'intrusive'] as ScanIntensity[]).map((i) => {
              const sel = p.intensity === i;
              return (
                <button
                  key={i}
                  type="button"
                  onClick={() => {
                    p.setIntensity(i);
                    p.resetScannersForIntensity(i);
                  }}
                  className={`flex items-center justify-between rounded-md border bg-bg-elevated p-3 text-left transition-colors ${
                    sel
                      ? 'border-brand/60 ring-1 ring-brand/30'
                      : 'border-bg-line hover:border-bg-line-strong'
                  }`}
                >
                  <span className="font-display text-sm font-medium capitalize text-text-primary">
                    {i}
                  </span>
                  {sel && <Icon.Check size={14} className="text-brand" />}
                </button>
              );
            })}
          </div>
          {p.intensity !== 'passive' && (
            <p className="mt-2 text-xs text-accent-warn">
              Active and intrusive scans require human-in-the-loop approval at run time.
            </p>
          )}
        </div>

        <div>
          <label className="mb-2 block text-2xs font-mono uppercase tracking-wider text-text-muted">
            Scanners
          </label>
          <div className="grid gap-2 sm:grid-cols-2">
            {(p.kind
              ? scannersForTargetKind(p.kind)
                  .filter((m) => m.intensities.includes(p.intensity))
                  .map((m) => m.id)
              : SCANNERS_BY_INTENSITY[p.intensity]
            ).map((s) => {
              const sel = p.scanners.includes(s);
              return (
                <label
                  key={s}
                  className={`flex cursor-pointer items-center gap-3 rounded-md border bg-bg-elevated px-3 py-2 transition-colors ${
                    sel ? 'border-brand/50' : 'border-bg-line hover:border-bg-line-strong'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={sel}
                    onChange={(e) =>
                      p.setScanners((cur) =>
                        e.target.checked
                          ? Array.from(new Set([...cur, s]))
                          : cur.filter((x) => x !== s)
                      )
                    }
                    className="accent-brand"
                  />
                  <span className="font-mono text-sm text-text-primary">{s}</span>
                </label>
              );
            })}
          </div>
        </div>

        <Field
          label="Schedule (cron, optional)"
          hint="Leave empty for on-demand only. Standard 5-field cron in UTC."
        >
          <input
            value={p.scheduleCron}
            onChange={(e) => p.setScheduleCron(e.target.value)}
            placeholder="0 2 * * *"
            className="ra-input font-mono"
          />
        </Field>
      </div>
    </Card>
  );
}

export type ReviewStepProps = {
  kind: TargetKind | null;
  name: string;
  targetValue: string;
  environment: string;
  owner: string;
  intensity: ScanIntensity;
  scanners: string[];
  scheduleCron: string;
  error: unknown;
};

export function ReviewStep(p: ReviewStepProps) {
  return (
    <Card title="Review & create" subtitle="Verify the target before saving">
      <dl className="grid gap-4 sm:grid-cols-2">
        <ReviewRow label="Kind" value={p.kind ? KIND_META[p.kind].label : '—'} />
        <ReviewRow label="Name" value={p.name || p.targetValue} />
        <ReviewRow label="Value" value={p.targetValue} mono />
        <ReviewRow label="Environment" value={p.environment} />
        <ReviewRow label="Owner" value={p.owner || '—'} />
        <ReviewRow label="Default intensity" value={p.intensity} />
        <ReviewRow
          label="Scanners"
          value={
            <div className="flex flex-wrap gap-1">
              {p.scanners.map((s) => (
                <Chip key={s}>{s}</Chip>
              ))}
            </div>
          }
        />
        <ReviewRow label="Schedule" value={p.scheduleCron || 'on-demand'} mono />
      </dl>
      {p.error !== null && p.error !== undefined && (
        <p className="mt-4 rounded border border-sev-critical/40 bg-sev-critical/10 px-3 py-2 text-sm text-sev-critical">
          {String(p.error)}
        </p>
      )}
    </Card>
  );
}
