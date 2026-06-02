import type { Finding } from '../../../../lib/api';
import { Chip } from '../../Badge';
import { Icon } from '../../Icon';

export function OverviewPanel({ f }: { f: Finding }) {
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
