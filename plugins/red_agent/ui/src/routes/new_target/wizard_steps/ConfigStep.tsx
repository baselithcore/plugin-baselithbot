import { type TargetKind } from '../../../lib/api';
import { Card, Icon } from '../../../components/ui';
import { CLOUD_PROVIDERS, type CloudProvider, Field } from './_shared';
import { HostConfig } from './HostConfig';

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
