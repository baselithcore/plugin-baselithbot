import type { Finding } from '../../../../lib/api';
import { Chip } from '../../Badge';
import { Icon } from '../../Icon';
import { evidenceStatus, formatEvidenceKey, isRecord, pickEntries, relTime } from '../utils';

export function EvidencePanel({
  finding,
  data,
}: {
  finding: Finding;
  data: Record<string, unknown>;
}) {
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
