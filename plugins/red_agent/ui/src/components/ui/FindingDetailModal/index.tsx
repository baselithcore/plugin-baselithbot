import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { api, type Finding, type FindingState } from '../../../lib/api';
import { Button } from '../Button';
import { Chip } from '../Badge';
import { Icon } from '../Icon';
import { Modal } from '../Modal';
import { SeverityBadge } from '../Badge';
import { ComplianceChips, RiskScoreChip, ThreatIntelChips } from './parts/chips';
import { EvidencePanel } from './parts/EvidencePanel';
import { GraphPanel } from './parts/GraphPanel';
import { KvBlock } from './parts/KvBlock';
import { OverviewPanel } from './parts/OverviewPanel';
import { ReplayPanel } from './parts/ReplayPanel';
import { STATE_OPTIONS } from './types';
import { isHttpUrl, relTime, severityHeaderCls } from './utils';

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
