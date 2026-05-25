import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { api, type Finding, type FindingState, type Severity } from '../../lib/api';
import { Button } from './Button';
import { Chip } from './Badge';
import { Icon } from './Icon';
import { MiniGraph } from './MiniGraph';
import { Modal } from './Modal';
import { SeverityBadge } from './Badge';

const STATE_OPTIONS: FindingState[] = ['open', 'triaged', 'fixed', 'wontfix', 'accepted'];

function relTime(iso: string | null): string {
  if (!iso) return '—';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

interface AttackTechnique {
  id: string;
  name: string;
}

function riskTone(score: number): 'critical' | 'warn' | 'brand' | 'neutral' {
  if (score >= 9) return 'critical';
  if (score >= 7) return 'warn';
  if (score >= 4) return 'brand';
  return 'neutral';
}

function RiskScoreChip({ score, evidence }: { score: number; evidence: Record<string, unknown> }) {
  const band = typeof evidence.risk_band === 'string' ? evidence.risk_band : null;
  return (
    <span title={`VPR-style risk score${band ? ` · ${band}` : ''}`}>
      <Chip tone={riskTone(score)}>
        <Icon.Activity size={11} />
        Risk {score.toFixed(1)}
        {band && <span className="opacity-75">· {band}</span>}
      </Chip>
    </span>
  );
}

function ThreatIntelChips({ evidence }: { evidence: Record<string, unknown> }) {
  const kev = evidence.kev_listed === true;
  const epssRaw = evidence.epss_score;
  const epss = typeof epssRaw === 'string' || typeof epssRaw === 'number' ? Number(epssRaw) : null;
  const techniques = Array.isArray(evidence.attack_techniques)
    ? (evidence.attack_techniques as AttackTechnique[]).slice(0, 2)
    : [];
  const reachableRaw = evidence.reachable;
  const reachable = typeof reachableRaw === 'boolean' ? reachableRaw : null;
  const vexStatusRaw = evidence.vex_status;
  const vexStatus =
    typeof vexStatusRaw === 'string' && vexStatusRaw.length > 0 ? vexStatusRaw : null;
  const greynoiseRaw = evidence.greynoise_classification;
  const greynoise =
    typeof greynoiseRaw === 'string' && greynoiseRaw.length > 0 ? greynoiseRaw : null;
  return (
    <>
      {kev && (
        <span title="CISA Known Exploited Vulnerabilities catalog">
          <Chip tone="critical">
            <Icon.Bug size={11} />
            KEV
          </Chip>
        </span>
      )}
      {epss != null && Number.isFinite(epss) && (
        <span title="FIRST EPSS exploitation probability (next 30 days)">
          <Chip tone={epss >= 0.5 ? 'critical' : epss >= 0.1 ? 'warn' : 'neutral'}>
            EPSS {(epss * 100).toFixed(1)}%
          </Chip>
        </span>
      )}
      {techniques.map((t) => (
        <span key={t.id} title={t.name}>
          <Chip>{t.id}</Chip>
        </span>
      ))}
      {reachable !== null && (
        <span
          title={
            reachable
              ? 'Vulnerable package referenced in source tree'
              : 'No call-graph or import reaches the vulnerable package'
          }
        >
          <Chip tone={reachable ? 'warn' : 'good'}>{reachable ? 'reachable' : 'unreachable'}</Chip>
        </span>
      )}
      {vexStatus && (
        <span title="VEX vendor attestation status">
          <Chip
            tone={
              vexStatus === 'not_affected' || vexStatus === 'fixed'
                ? 'good'
                : vexStatus === 'affected'
                  ? 'critical'
                  : 'neutral'
            }
          >
            VEX {vexStatus.replace(/_/g, ' ')}
          </Chip>
        </span>
      )}
      {greynoise && (
        <span title="GreyNoise reputation classification">
          <Chip tone={greynoise === 'malicious' ? 'critical' : 'neutral'}>GN {greynoise}</Chip>
        </span>
      )}
    </>
  );
}

function ComplianceChips({ controls }: { controls: string[] }) {
  if (!controls.length) return null;
  const visible = controls.slice(0, 4);
  const overflow = controls.length - visible.length;
  return (
    <>
      {visible.map((c) => (
        <span key={c} title="Compliance control">
          <Chip tone="good">
            <Icon.ShieldCheck size={11} />
            {c}
          </Chip>
        </span>
      ))}
      {overflow > 0 && <Chip tone="neutral">+{overflow}</Chip>}
    </>
  );
}

function severityHeaderCls(s: Severity): string {
  switch (s) {
    case 'critical':
      return 'border-sev-critical/40 bg-gradient-to-r from-sev-critical/15 to-transparent';
    case 'high':
      return 'border-accent-warn/40 bg-gradient-to-r from-accent-warn/15 to-transparent';
    case 'medium':
      return 'border-sev-medium/40 bg-gradient-to-r from-sev-medium/15 to-transparent';
    case 'low':
      return 'border-sev-low/40 bg-gradient-to-r from-sev-low/15 to-transparent';
    default:
      return 'border-bg-line bg-gradient-to-r from-bg-overlay to-transparent';
  }
}

export function FindingDetailModal({
  finding,
  open,
  onClose,
}: {
  finding: Finding | null;
  open: boolean;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<'overview' | 'graph' | 'evidence' | 'replay' | 'raw'>(
    'overview'
  );

  const isPartial =
    finding != null &&
    (finding.evidence as Record<string, unknown> | undefined)?.source === 'graph_fallback';

  const graphQ = useQuery({
    queryKey: ['finding-graph', finding?.id],
    queryFn: () => api.getFindingGraph(finding!.id, 2),
    enabled: Boolean(finding && activeTab === 'graph' && !isPartial),
    staleTime: 0,
    refetchOnMount: 'always',
  });

  const evidenceQ = useQuery({
    queryKey: ['finding-evidence', finding?.id],
    queryFn: () => api.getFindingEvidence(finding!.id, 500),
    enabled: Boolean(finding && activeTab === 'replay' && !isPartial),
    staleTime: 30_000,
  });

  const triage = useMutation({
    mutationFn: (vars: { state?: FindingState; notes?: string; assignee?: string }) =>
      api.updateFinding(finding!.id, vars),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['findings'] });
      qc.invalidateQueries({ queryKey: ['target-findings'] });
    },
  });

  const [autopr, setAutopr] = useState<{
    status: 'idle' | 'pending' | 'success' | 'error';
    message?: string;
    pr_url?: string | null;
  }>({ status: 'idle' });
  const autoRemediate = useMutation({
    mutationFn: () => api.autoRemediateFinding(finding!.id),
    onMutate: () => setAutopr({ status: 'pending' }),
    onSuccess: (res) =>
      setAutopr({ status: 'success', pr_url: res.pr_url, message: res.fixed_version ?? undefined }),
    onError: (err: Error) => setAutopr({ status: 'error', message: err.message }),
  });

  const [notesDraft, setNotesDraft] = useState<string>('');
  const [assigneeDraft, setAssigneeDraft] = useState<string>('');

  if (!finding) return null;

  const f = finding;
  const evidence = (f.evidence ?? {}) as Record<string, unknown>;
  const raw = (f.raw ?? {}) as Record<string, unknown>;
  const hasEvidence = Object.keys(evidence).length > 0;
  const hasRaw = Object.keys(raw).length > 0;
  const overdue = f.due_at && new Date(f.due_at).getTime() < Date.now();
  const autoprEligible =
    Array.isArray(evidence.osv_fixed_in) &&
    (evidence.osv_fixed_in as unknown[]).length > 0 &&
    typeof evidence.package === 'string' &&
    (typeof evidence.repo_owner === 'string' ||
      (typeof evidence.repo === 'object' &&
        evidence.repo !== null &&
        typeof (evidence.repo as Record<string, unknown>).owner === 'string'));

  return (
    <Modal open={open} onClose={onClose} size="xl" ariaLabel="Finding details">
      <div className={`flex flex-col gap-3 border-b ${severityHeaderCls(f.severity)} px-6 py-5`}>
        <div className="flex items-center gap-3">
          <SeverityBadge severity={f.severity} full />
          <Chip>{f.scanner}</Chip>
          {f.cve && (
            <Chip tone="warn">
              <Icon.Bug size={11} />
              {f.cve}
            </Chip>
          )}
          {f.cwe && <Chip>CWE-{f.cwe.replace(/^CWE-/, '')}</Chip>}
          {f.cvss_score != null && (
            <Chip tone={f.cvss_score >= 7 ? 'critical' : f.cvss_score >= 4 ? 'warn' : 'neutral'}>
              CVSS {f.cvss_score.toFixed(1)}
            </Chip>
          )}
          {f.risk_score != null && Number.isFinite(f.risk_score) && (
            <RiskScoreChip
              score={f.risk_score}
              evidence={(f.evidence ?? {}) as Record<string, unknown>}
            />
          )}
          <ThreatIntelChips evidence={(f.evidence ?? {}) as Record<string, unknown>} />
          <ComplianceChips controls={f.controls ?? []} />
          <span className="ml-auto font-mono text-2xs text-text-muted">{f.id.slice(0, 8)}</span>
        </div>
        <h2 className="font-display text-xl font-medium text-text-primary">{f.title}</h2>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-xs text-text-muted">
          <span className="inline-flex items-center gap-1.5">
            <Icon.Target size={11} />
            {f.endpoint ?? f.target}
          </span>
          {f.port && (
            <span className="inline-flex items-center gap-1.5">
              <Icon.Network size={11} />
              {f.port}/{f.service ?? 'tcp'}
            </span>
          )}
          <span className="inline-flex items-center gap-1.5">
            <Icon.Clock size={11} />
            discovered {relTime(f.discovered_at)}
          </span>
          {f.due_at && (
            <span
              className={`inline-flex items-center gap-1.5 ${overdue ? 'text-sev-critical' : ''}`}
            >
              <Icon.Activity size={11} />
              SLA {overdue ? 'overdue' : 'due'} {relTime(f.due_at)}
            </span>
          )}
        </div>
      </div>

      <div className="flex overflow-x-auto border-b border-bg-line px-4">
        {(
          [
            { id: 'overview', label: 'Overview', shortLabel: 'Overview' },
            { id: 'graph', label: 'Graph', shortLabel: 'Graph' },
            {
              id: 'evidence',
              label: `Evidence ${hasEvidence ? `(${Object.keys(evidence).length})` : ''}`,
              shortLabel: 'Evidence',
            },
            { id: 'replay', label: 'Replay', shortLabel: 'Replay' },
            { id: 'raw', label: hasRaw ? 'Raw' : 'Raw (empty)', shortLabel: 'Raw' },
          ] as const
        ).map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setActiveTab(t.id)}
            className={`relative shrink-0 whitespace-nowrap px-3 py-2.5 text-xs font-mono uppercase tracking-wider transition-colors ${
              activeTab === t.id ? 'text-brand' : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <span className="hidden sm:inline">{t.label}</span>
            <span className="sm:hidden">{t.shortLabel}</span>
            {activeTab === t.id && (
              <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-t bg-brand" />
            )}
          </button>
        ))}
      </div>

      <div
        className={
          activeTab === 'graph'
            ? 'h-[65vh] overflow-hidden px-3 py-3'
            : 'max-h-[55vh] overflow-y-auto px-6 py-5'
        }
      >
        {activeTab === 'overview' && <OverviewPanel f={f} />}
        {activeTab === 'graph' && (
          <GraphPanel
            findingId={f.id}
            data={graphQ.data}
            isLoading={graphQ.isLoading}
            error={graphQ.error as Error | null}
            partial={isPartial}
          />
        )}
        {activeTab === 'evidence' && <EvidencePanel finding={f} data={evidence} />}
        {activeTab === 'replay' && (
          <ReplayPanel
            data={evidenceQ.data}
            isLoading={evidenceQ.isLoading}
            error={evidenceQ.error as Error | null}
            partial={isPartial}
          />
        )}
        {activeTab === 'raw' && <KvBlock data={raw} empty="No raw scanner output stored." raw />}
      </div>

      <div className="border-t border-bg-line bg-bg-base/50 px-6 py-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="block">
            <span className="mb-1 block text-2xs font-mono uppercase tracking-wider text-text-muted">
              State
            </span>
            <select
              value={f.state}
              onChange={(e) => triage.mutate({ state: e.target.value as FindingState })}
              className="ra-select w-full"
              disabled={triage.isPending}
            >
              {STATE_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-2xs font-mono uppercase tracking-wider text-text-muted">
              Assignee
            </span>
            <input
              defaultValue={f.assignee ?? ''}
              onChange={(e) => setAssigneeDraft(e.target.value)}
              onBlur={() => {
                if (assigneeDraft !== f.assignee) triage.mutate({ assignee: assigneeDraft });
              }}
              placeholder="team@acme.com"
              className="ra-input w-full"
            />
          </label>
          <div>
            <span className="mb-1 block text-2xs font-mono uppercase tracking-wider text-text-muted">
              Lifecycle
            </span>
            <div className="font-mono text-xs text-text-secondary">
              <div>discovered {relTime(f.discovered_at)}</div>
              {f.triaged_at && <div>triaged {relTime(f.triaged_at)}</div>}
              {f.resolved_at && <div>resolved {relTime(f.resolved_at)}</div>}
            </div>
          </div>
        </div>
        <div className="mt-3">
          <span className="mb-1 block text-2xs font-mono uppercase tracking-wider text-text-muted">
            Notes
          </span>
          <textarea
            defaultValue={f.notes ?? ''}
            onChange={(e) => setNotesDraft(e.target.value)}
            onBlur={() => {
              if (notesDraft !== (f.notes ?? '')) triage.mutate({ notes: notesDraft });
            }}
            placeholder="Triage notes — saved on blur."
            rows={2}
            className="ra-input w-full resize-y min-h-[60px]"
          />
        </div>
        {autopr.status !== 'idle' && (
          <div
            className={`mt-3 rounded border px-3 py-2 text-xs font-mono ${
              autopr.status === 'success'
                ? 'border-status-success/40 bg-status-success/10 text-status-success'
                : autopr.status === 'error'
                  ? 'border-sev-critical/40 bg-sev-critical/10 text-sev-critical'
                  : 'border-bg-line bg-bg-overlay text-text-secondary'
            }`}
            role="status"
          >
            {autopr.status === 'pending' && 'Opening auto-remediation PR…'}
            {autopr.status === 'success' &&
              (autopr.pr_url ? (
                <a
                  href={autopr.pr_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline"
                >
                  PR opened — bumped to {autopr.message ?? 'fixed version'}
                </a>
              ) : (
                `PR opened${autopr.message ? ` — bumped to ${autopr.message}` : ''}.`
              ))}
            {autopr.status === 'error' && `Auto-remediation failed: ${autopr.message ?? '—'}`}
          </div>
        )}
        <div className="mt-3 flex flex-wrap items-center justify-end gap-2">
          {f.external_ref && (
            <a
              href={isHttpUrl(f.external_ref) ? f.external_ref : '#'}
              target={isHttpUrl(f.external_ref) ? '_blank' : undefined}
              rel="noopener noreferrer"
              className="ra-btn ra-btn-ghost ra-btn-sm"
              title="External tracker reference (Jira/ServiceNow/Linear/GitHub)"
            >
              <Icon.ArrowRight size={12} />
              {f.external_ref.length > 32 ? `${f.external_ref.slice(0, 32)}…` : f.external_ref}
            </a>
          )}
          {f.cve && (
            <>
              <a
                href={`https://nvd.nist.gov/vuln/detail/${f.cve}`}
                target="_blank"
                rel="noopener noreferrer"
                className="ra-btn ra-btn-ghost ra-btn-sm"
              >
                <Icon.ArrowRight size={12} />
                NVD
              </a>
              <a
                href={`https://api.first.org/data/v1/epss?cve=${f.cve}`}
                target="_blank"
                rel="noopener noreferrer"
                className="ra-btn ra-btn-ghost ra-btn-sm"
                title="FIRST EPSS exploit prediction"
              >
                EPSS
              </a>
              {f.evidence?.kev_listed === true && (
                <a
                  href="https://www.cisa.gov/known-exploited-vulnerabilities-catalog"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ra-btn ra-btn-ghost ra-btn-sm"
                  title="CISA Known Exploited Vulnerabilities catalog"
                >
                  CISA KEV
                </a>
              )}
            </>
          )}
          {autoprEligible && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => autoRemediate.mutate()}
              disabled={autoRemediate.isPending || autopr.status === 'success'}
              title="Open a fix-PR on the upstream repository (requires GitHub token + repo metadata)"
            >
              <Icon.Bolt size={12} />
              {autoRemediate.isPending ? 'Opening PR…' : 'Auto-remediate'}
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function GraphPanel({
  findingId,
  data,
  isLoading,
  error,
  partial = false,
}: {
  findingId: string;
  data: import('../../lib/api').AttackSurfaceResp | undefined;
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

function OverviewPanel({ f }: { f: Finding }) {
  return (
    <div className="space-y-5">
      {f.description && (
        <Section title="Description">
          <p className="whitespace-pre-line text-sm leading-relaxed text-text-primary">
            {f.description}
          </p>
        </Section>
      )}
      {f.remediation && (
        <Section title="Remediation">
          <p className="whitespace-pre-line text-sm leading-relaxed text-text-primary">
            {f.remediation}
          </p>
        </Section>
      )}
      <Section title="Identifiers">
        <dl className="grid gap-3 sm:grid-cols-2">
          <Row label="Scanner" value={f.scanner} mono />
          <Row label="Severity" value={f.severity} mono />
          <Row label="CVE" value={f.cve ?? '—'} mono />
          <Row label="CWE" value={f.cwe ?? '—'} mono />
          <Row label="CVSS" value={f.cvss_score != null ? f.cvss_score.toFixed(1) : '—'} mono />
          <Row
            label="Risk score"
            value={
              f.risk_score != null && Number.isFinite(f.risk_score) ? f.risk_score.toFixed(1) : '—'
            }
            mono
          />
          <Row label="Finding ID" value={f.id} mono />
          <Row label="Target" value={f.target} mono />
          <Row label="Endpoint" value={f.endpoint ?? '—'} mono />
          <Row label="External ref" value={f.external_ref ?? '—'} mono />
        </dl>
      </Section>
      {(f.controls ?? []).length > 0 && (
        <Section title="Compliance controls">
          <div className="flex flex-wrap gap-1.5">
            {f.controls.map((c) => (
              <Chip key={c} tone="good">
                <Icon.ShieldCheck size={11} />
                {c}
              </Chip>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="mb-2 text-2xs font-mono uppercase tracking-wider text-text-muted">{title}</h3>
      <div>{children}</div>
    </section>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-2xs font-mono uppercase tracking-wider text-text-muted">{label}</dt>
      <dd className={`mt-1 truncate text-sm text-text-primary ${mono ? 'font-mono' : ''}`}>
        {value}
      </dd>
    </div>
  );
}

const SIGMA_OVERRIDE_KEY = (findingId: string) => `red_agent.sigma.overrides.${findingId}`;

function _loadSigmaOverride(findingId: string): { keywords: string; tags: string } {
  try {
    const raw = localStorage.getItem(SIGMA_OVERRIDE_KEY(findingId));
    if (!raw) return { keywords: '', tags: '' };
    const parsed = JSON.parse(raw) as { keywords?: string; tags?: string };
    return { keywords: parsed.keywords ?? '', tags: parsed.tags ?? '' };
  } catch {
    return { keywords: '', tags: '' };
  }
}

function _saveSigmaOverride(findingId: string, payload: { keywords: string; tags: string }): void {
  try {
    if (!payload.keywords.trim() && !payload.tags.trim()) {
      localStorage.removeItem(SIGMA_OVERRIDE_KEY(findingId));
      return;
    }
    localStorage.setItem(SIGMA_OVERRIDE_KEY(findingId), JSON.stringify(payload));
  } catch {
    /* localStorage may be disabled — ignore */
  }
}

function SigmaDownload({ findingId }: { findingId: string }) {
  const [open, setOpen] = useState(false);
  const initial = useMemo(() => _loadSigmaOverride(findingId), [findingId]);
  const [keywords, setKeywords] = useState(initial.keywords);
  const [tags, setTags] = useState(initial.tags);
  useEffect(() => {
    _saveSigmaOverride(findingId, { keywords, tags });
  }, [findingId, keywords, tags]);
  const customized = Boolean(keywords.trim() || tags.trim());
  const url = api.findingSigmaUrlWithOverrides(findingId, {
    keywords: keywords
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean),
    tags: tags
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean),
  });
  return (
    <div className="relative">
      <div className="flex items-center gap-1">
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          download
          className="ra-btn ra-btn-ghost ra-btn-sm"
        >
          <Icon.Download size={12} />
          Sigma rule
          {customized && <Chip tone="brand">edited</Chip>}
        </a>
        <button
          type="button"
          onClick={() => setOpen((x) => !x)}
          className="ra-btn ra-btn-ghost ra-btn-sm px-1.5"
          title="Customize keywords / tags"
        >
          <Icon.ChevronDown
            size={12}
            className={open ? 'rotate-180 transition-transform' : 'transition-transform'}
          />
        </button>
      </div>
      {open && (
        <div className="absolute right-0 z-20 mt-1 w-72 rounded border border-bg-line bg-bg-elevated p-3 shadow-lg">
          <label className="mb-1 block text-2xs font-mono uppercase tracking-wider text-text-muted">
            Keywords (one per line)
          </label>
          <textarea
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            className="ra-input min-h-[80px] font-mono text-2xs"
            placeholder={'UNION SELECT\nOR 1=1'}
          />
          <label className="mt-2 mb-1 block text-2xs font-mono uppercase tracking-wider text-text-muted">
            Tags (comma-separated)
          </label>
          <input
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            className="ra-input font-mono text-2xs"
            placeholder="team.appsec, q2-pentest"
          />
          <div className="mt-2 flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={() => {
                setKeywords('');
                setTags('');
              }}
              className="text-2xs text-text-muted hover:text-text-primary"
              disabled={!customized}
            >
              reset
            </button>
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              download
              onClick={() => setOpen(false)}
              className="ra-btn ra-btn-primary ra-btn-sm"
            >
              <Icon.Download size={12} />
              Download
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

function ReplayPanel({
  data,
  isLoading,
  error,
  partial = false,
}: {
  data: import('../../lib/api').FindingEvidence | undefined;
  isLoading: boolean;
  error: Error | null;
  partial?: boolean;
}) {
  if (partial) {
    return (
      <div className="rounded border border-bg-line bg-bg-overlay/40 p-4 text-sm text-text-secondary">
        <div className="font-mono text-2xs uppercase tracking-wider text-text-muted">
          Replay unavailable
        </div>
        <p className="mt-2">
          This finding is reconstructed from the attack-surface graph. The relational audit chain is
          not available — likely the scan record was purged or persistence was unavailable when the
          finding was upserted.
        </p>
      </div>
    );
  }
  if (isLoading) {
    return (
      <div className="grid place-items-center py-8 text-sm text-text-muted">
        <span className="font-mono">Loading audit chain…</span>
      </div>
    );
  }
  if (error) {
    return (
      <div className="rounded border border-sev-critical/40 bg-sev-critical/10 p-3 text-sm text-sev-critical">
        {String(error)}
      </div>
    );
  }
  if (!data) {
    return (
      <div className="grid place-items-center py-8 text-sm text-text-muted">
        <span className="font-mono">No replay data.</span>
      </div>
    );
  }
  const tones: Record<string, string> = {
    'scan.roe_violation': 'border-sev-critical/40 bg-sev-critical/10',
    'scan.roe_adjusted': 'border-sev-medium/40 bg-sev-medium/10',
    'scan.critic_veto': 'border-sev-critical/40 bg-sev-critical/10',
    'scan.critic_amended': 'border-sev-medium/40 bg-sev-medium/10',
    'scan.guardrail_violation': 'border-sev-critical/40 bg-sev-critical/10',
    'scan.hitl_denied': 'border-sev-critical/40 bg-sev-critical/10',
    'scan.hitl_timeout': 'border-sev-medium/40 bg-sev-medium/10',
  };
  const sigmaAvailable = Boolean(
    (data.finding.evidence as Record<string, unknown> | undefined)?.detection_guidance
  );
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3 text-xs text-text-muted">
        <span>
          Scan <span className="font-mono text-text-primary">{data.scan_id.slice(0, 12)}</span>
        </span>
        <div className="flex items-center gap-3">
          {sigmaAvailable && <SigmaDownload findingId={data.finding.id} />}
          <span className="font-mono">{data.chain.length} events</span>
        </div>
      </div>
      {data.chain.length === 0 ? (
        <div className="rounded border border-bg-line/60 bg-bg-overlay p-3 text-sm text-text-muted">
          No audit events recorded for this scan.
        </div>
      ) : (
        <ol className="space-y-2">
          {data.chain.map((ev) => (
            <li
              key={ev.id}
              className={`rounded border p-3 ${
                tones[ev.event] ?? 'border-bg-line/60 bg-bg-overlay'
              }`}
            >
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono text-text-primary">{ev.event}</span>
                <span className="font-mono text-2xs text-text-muted">
                  {ev.created_at ? new Date(ev.created_at).toLocaleString() : ''}
                </span>
              </div>
              {ev.actor && (
                <div className="mt-1 text-2xs text-text-muted">
                  by <span className="font-mono">{ev.actor}</span>
                </div>
              )}
              {Object.keys(ev.payload ?? {}).length > 0 && (
                <pre className="mt-2 max-h-40 overflow-auto rounded bg-bg-base/60 p-2 font-mono text-2xs leading-snug text-text-secondary">
                  {JSON.stringify(ev.payload, null, 2)}
                </pre>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function EvidencePanel({ finding, data }: { finding: Finding; data: Record<string, unknown> }) {
  const entries = Object.entries(data);

  if (entries.length === 0) {
    return (
      <div className="grid place-items-center rounded-lg border border-bg-line bg-bg-base/50 py-12 text-sm text-text-muted">
        No evidence captured.
      </div>
    );
  }

  const status = evidenceStatus(data);
  const scannerKeys = [
    'matcher',
    'template',
    'tags',
    'method',
    'param',
    'evidence',
    'matched',
    'extracted_results',
  ];
  const assetKeys = [
    'package',
    'installed_version',
    'fixed_version',
    'product',
    'version',
    'protocol',
  ];
  const analysisKeys = [
    'confirmed',
    'scanner_failure',
    'exception_type',
    'message',
    'duplicate_of',
    'duplicate_score',
    'ml_fp_score',
    'triage_llm',
  ];
  const threatIntelKeys = [
    'kev_listed',
    'kev_due_date',
    'kev_short_description',
    'kev_required_action',
    'epss_score',
    'epss_percentile',
    'attack_techniques',
    'osv_fixed_in',
    'osv_aliases',
    'osv_advisory_url',
    'greynoise_classification',
    'greynoise_noise',
    'greynoise_riot',
  ];
  const complianceKeys = ['compliance_violation', 'compliance_recommendation', 'controls'];
  const riskKeys = [
    'risk_score',
    'risk_band',
    'risk_factors',
    'reachable',
    'reachable_paths',
    'vex_status',
    'vex_justification',
    'vex_document',
  ];
  const rendered = new Set<string>();

  const scanner = pickEntries(data, scannerKeys, rendered);
  const asset = pickEntries(data, assetKeys, rendered);
  const analysis = pickEntries(data, analysisKeys, rendered);
  const threatIntel = pickEntries(data, threatIntelKeys, rendered);
  const compliance = pickEntries(data, complianceKeys, rendered);
  const risk = pickEntries(data, riskKeys, rendered);
  const remaining = entries.filter(([k]) => !rendered.has(k));

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <EvidenceStat
          icon={<Icon.ShieldCheck size={14} />}
          label="Validation"
          value={status.label}
          tone={status.tone}
        />
        <EvidenceStat
          icon={<Icon.Scans size={14} />}
          label="Source"
          value={finding.scanner}
          tone="brand"
        />
        <EvidenceStat
          icon={<Icon.Folder size={14} />}
          label="Artifacts"
          value={String(entries.length)}
          tone="neutral"
        />
      </div>

      <section className="rounded-lg border border-bg-line bg-bg-base/50">
        <div className="grid gap-3 p-4 sm:grid-cols-3">
          <EvidenceContext label="Target" value={finding.target} />
          <EvidenceContext label="Endpoint" value={finding.endpoint ?? '—'} />
          <EvidenceContext
            label="Observed"
            value={`${finding.port ? `${finding.port}/${finding.service ?? 'tcp'} · ` : ''}${relTime(
              finding.discovered_at
            )}`}
          />
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        {risk.length > 0 && <EvidenceSection title="Risk · Reachability · VEX" entries={risk} />}
        {threatIntel.length > 0 && (
          <EvidenceSection
            title="Threat intel (EPSS · KEV · ATT&CK · OSV · GreyNoise)"
            entries={threatIntel}
          />
        )}
        {compliance.length > 0 && <EvidenceSection title="Compliance" entries={compliance} />}
        {scanner.length > 0 && <EvidenceSection title="Scanner signals" entries={scanner} />}
        {asset.length > 0 && <EvidenceSection title="Asset fingerprint" entries={asset} />}
        {analysis.length > 0 && (
          <EvidenceSection title="Validation and triage" entries={analysis} />
        )}
        {remaining.length > 0 && (
          <EvidenceSection title="Additional artifacts" entries={remaining} />
        )}
      </div>
    </div>
  );
}

function pickEntries(
  data: Record<string, unknown>,
  keys: string[],
  rendered: Set<string>
): [string, unknown][] {
  const out: [string, unknown][] = [];
  for (const key of keys) {
    if (!(key in data)) continue;
    rendered.add(key);
    out.push([key, data[key]]);
  }
  return out;
}

function evidenceStatus(data: Record<string, unknown>): {
  label: string;
  tone: 'neutral' | 'brand' | 'warn' | 'critical' | 'good';
} {
  if (data.scanner_failure) return { label: 'Scanner failure', tone: 'warn' };
  if (data.confirmed) return { label: 'Confirmed', tone: 'good' };
  const triage = data.triage_llm;
  if (isRecord(triage) && typeof triage.verdict === 'string') {
    const verdict = triage.verdict.replace(/_/g, ' ');
    return {
      label: verdict,
      tone: verdict.includes('false') ? 'warn' : verdict.includes('confirmed') ? 'good' : 'brand',
    };
  }
  if ('ml_fp_score' in data) return { label: 'ML scored', tone: 'brand' };
  return { label: 'Captured', tone: 'neutral' };
}

function EvidenceStat({
  icon,
  label,
  value,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone: 'neutral' | 'brand' | 'warn' | 'critical' | 'good';
}) {
  const toneClass = {
    neutral: 'border-bg-line bg-bg-base/60 text-text-primary',
    brand: 'border-brand/30 bg-brand/10 text-brand',
    warn: 'border-accent-warn/30 bg-accent-warn/10 text-accent-warn',
    critical: 'border-sev-critical/30 bg-sev-critical/10 text-sev-critical',
    good: 'border-status-success/30 bg-status-success/10 text-status-success',
  }[tone];

  return (
    <div className={`rounded-lg border px-4 py-3 ${toneClass}`}>
      <div className="flex items-center justify-between gap-3">
        <span className="text-2xs font-mono uppercase tracking-wider opacity-75">{label}</span>
        {icon}
      </div>
      <div className="mt-2 truncate font-display text-lg font-medium">{value}</div>
    </div>
  );
}

function EvidenceContext({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <div className="text-2xs font-mono uppercase tracking-wider text-text-muted">{label}</div>
      <div className="mt-1 break-all font-mono text-sm text-text-primary">{value}</div>
    </div>
  );
}

function EvidenceSection({ title, entries }: { title: string; entries: [string, unknown][] }) {
  return (
    <section className="overflow-hidden rounded-lg border border-bg-line bg-bg-card">
      <header className="border-b border-bg-line/70 px-4 py-3">
        <h3 className="font-display text-sm font-medium text-text-primary">{title}</h3>
      </header>
      <div className="divide-y divide-bg-line/60">
        {entries.map(([key, value]) => (
          <div key={key} className="grid gap-2 px-4 py-3 sm:grid-cols-[150px_1fr]">
            <dt className="text-2xs font-mono uppercase tracking-wider text-text-muted">
              {formatEvidenceKey(key)}
            </dt>
            <dd className="min-w-0">{renderEvidenceValue(value)}</dd>
          </div>
        ))}
      </div>
    </section>
  );
}

function renderEvidenceValue(value: unknown): React.ReactNode {
  if (value === null || value === undefined || value === '') {
    return <span className="font-mono text-xs text-text-muted">—</span>;
  }
  if (typeof value === 'boolean') {
    return (
      <Chip tone={value ? 'good' : 'neutral'} className="uppercase">
        {String(value)}
      </Chip>
    );
  }
  if (typeof value === 'number') {
    return <span className="font-mono text-sm tabular-nums text-text-primary">{value}</span>;
  }
  if (typeof value === 'string') {
    return (
      <span className="break-words font-mono text-sm leading-relaxed text-text-primary">
        {value}
      </span>
    );
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="font-mono text-xs text-text-muted">empty</span>;
    const allScalar = value.every(
      (x) => x === null || ['string', 'number', 'boolean'].includes(typeof x)
    );
    if (allScalar) {
      return (
        <div className="flex flex-wrap gap-1.5">
          {value.map((item, idx) => (
            <Chip key={`${String(item)}-${idx}`}>{String(item)}</Chip>
          ))}
        </div>
      );
    }
    const allTechniques = value.every(
      (x) => isRecord(x) && typeof x.id === 'string' && typeof x.name === 'string'
    );
    if (allTechniques) {
      return (
        <div className="flex flex-wrap gap-1.5">
          {(value as { id: string; name: string }[]).map((t) => (
            <a
              key={t.id}
              href={`https://attack.mitre.org/techniques/${t.id.replace(/\./g, '/')}/`}
              target="_blank"
              rel="noopener noreferrer"
              title={t.name}
            >
              <Chip tone="brand">
                {t.id} · {t.name}
              </Chip>
            </a>
          ))}
        </div>
      );
    }
  }
  return (
    <pre className="max-h-52 overflow-auto rounded-md border border-bg-line bg-bg-base px-3 py-2 font-mono text-xs leading-relaxed text-text-secondary">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function formatEvidenceKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase());
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isHttpUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

function KvBlock({
  data,
  empty,
  raw,
}: {
  data: Record<string, unknown>;
  empty: string;
  raw?: boolean;
}) {
  if (Object.keys(data).length === 0) {
    return <div className="grid place-items-center py-12 text-sm text-text-muted">{empty}</div>;
  }
  if (raw) {
    return (
      <pre className="overflow-x-auto rounded border border-bg-line bg-bg-base px-3 py-2.5 font-mono text-xs leading-relaxed text-text-secondary">
        {JSON.stringify(data, null, 2)}
      </pre>
    );
  }
  return (
    <dl className="space-y-2">
      {Object.entries(data).map(([k, v]) => (
        <div
          key={k}
          className="grid gap-1 rounded border border-bg-line/60 bg-bg-base/50 px-3 py-2 sm:grid-cols-[200px_1fr]"
        >
          <dt className="text-2xs font-mono uppercase tracking-wider text-text-muted">{k}</dt>
          <dd className="font-mono text-xs text-text-primary break-words">
            {typeof v === 'object' && v !== null ? (
              <pre className="whitespace-pre-wrap">{JSON.stringify(v, null, 2)}</pre>
            ) : (
              String(v)
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}
