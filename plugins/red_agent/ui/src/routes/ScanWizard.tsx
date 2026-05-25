import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api, type PreflightBody, type PreflightResp } from '../lib/api';
import { Button, Card, Chip, Icon, PageHeader } from '../components/ui';
import { SCANNERS_BY_INTENSITY as REGISTRY_SCANNERS_BY_INTENSITY } from '../lib/scanners';

const SCANNERS_BY_INTENSITY: Record<PreflightBody['intensity'], string[]> =
  REGISTRY_SCANNERS_BY_INTENSITY;

const STEPS = ['Target', 'Pre-flight', 'Scanners', 'Confirm'] as const;

const INTENSITY_DESC: Record<
  PreflightBody['intensity'],
  { label: string; sub: string; tone: string }
> = {
  passive: {
    label: 'Passive',
    sub: 'Read-only recon. Safe defaults.',
    tone: 'border-bg-line hover:border-status-success/40',
  },
  active: {
    label: 'Active',
    sub: 'Probing & fuzzing. Requires HITL approval.',
    tone: 'border-bg-line hover:border-accent-warn/40',
  },
  intrusive: {
    label: 'Intrusive',
    sub: 'Exploit attempts. Requires HITL approval.',
    tone: 'border-bg-line hover:border-sev-critical/40',
  },
};

export function ScanWizard() {
  const nav = useNavigate();
  const [step, setStep] = useState<0 | 1 | 2 | 3>(0);
  const [target, setTarget] = useState('');
  const [engagementId, setEngagementId] = useState('');
  const [intensity, setIntensity] = useState<PreflightBody['intensity']>('passive');
  const [scanners, setScanners] = useState<string[]>(SCANNERS_BY_INTENSITY.passive);
  const [pre, setPre] = useState<PreflightResp | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const engagements = useQuery({
    queryKey: ['engagements', 'scan-wizard'],
    queryFn: () => api.listEngagements({ limit: 100 }),
  });

  function targetType(v: string): PreflightBody['target']['type'] {
    if (v.startsWith('http://') || v.startsWith('https://')) return 'url';
    if (/^\d+\.\d+\.\d+\.\d+(\/\d+)?$/.test(v)) return v.includes('/') ? 'cidr' : 'ip';
    return 'hostname';
  }

  async function runPreflight() {
    setErr(null);
    setBusy(true);
    try {
      const res = await api.preflight({
        target: { type: targetType(target), value: target },
        scanners,
        intensity,
      });
      setPre(res);
      setStep(2);
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function submit() {
    setErr(null);
    setBusy(true);
    try {
      const r = await api.createScan({
        target: { type: targetType(target), value: target },
        engagement_id: engagementId || null,
        scanners,
        intensity,
      });
      nav(`/scans/${r.scan_id}`);
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="New scan"
        description="Configure target, intensity, and scanners. Pre-flight enforces scope and HITL gates."
        breadcrumbs={[{ label: 'Scans' }, { label: 'New' }]}
      />

      <ol className="flex flex-wrap gap-2">
        {STEPS.map((s, i) => {
          const active = i === step;
          const done = i < step;
          return (
            <li
              key={s}
              className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs font-mono transition-colors ${
                active
                  ? 'border-brand/60 bg-brand/10 text-brand shadow-glow-soft'
                  : done
                    ? 'border-status-success/40 bg-status-success/10 text-status-success'
                    : 'border-bg-line bg-bg-elevated text-text-muted'
              }`}
            >
              <span className="grid h-4 w-4 place-items-center rounded-full bg-current/20 text-2xs font-semibold">
                {done ? <Icon.Check size={10} /> : i + 1}
              </span>
              <span className="uppercase tracking-wider">{s}</span>
            </li>
          );
        })}
      </ol>

      {step === 0 && (
        <Card title="Target & intensity">
          <div className="space-y-5">
            <div>
              <label className="mb-1.5 block text-2xs font-mono uppercase tracking-wider text-text-muted">
                Target (URL, hostname, IP or CIDR)
              </label>
              <input
                type="text"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="https://api.example.com  ·  example.com  ·  10.0.0.0/24"
                className="ra-input"
              />
              <p className="mt-1.5 text-xs text-text-muted">
                Detected type:{' '}
                <span className="font-mono text-text-secondary">
                  {target ? targetType(target) : '—'}
                </span>
              </p>
            </div>
            <div>
              <label className="mb-1.5 block text-2xs font-mono uppercase tracking-wider text-text-muted">
                Engagement
              </label>
              <select
                value={engagementId}
                onChange={(e) => setEngagementId(e.target.value)}
                className="ra-select"
              >
                <option value="">No engagement</option>
                {(engagements.data ?? []).map((engagement) => (
                  <option key={engagement.id} value={engagement.id}>
                    {engagement.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-2xs font-mono uppercase tracking-wider text-text-muted">
                Intensity
              </label>
              <div className="grid gap-2 sm:grid-cols-3">
                {(Object.keys(INTENSITY_DESC) as PreflightBody['intensity'][]).map((k) => {
                  const sel = intensity === k;
                  const meta = INTENSITY_DESC[k];
                  return (
                    <button
                      key={k}
                      type="button"
                      onClick={() => {
                        setIntensity(k);
                        setScanners(SCANNERS_BY_INTENSITY[k]);
                      }}
                      className={`text-left rounded-md border bg-bg-elevated p-3 transition-colors ${
                        sel ? 'border-brand/60 ring-1 ring-brand/30' : meta.tone
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="font-display text-sm font-medium text-text-primary">
                          {meta.label}
                        </div>
                        {sel && <Icon.Check size={14} className="text-brand" />}
                      </div>
                      <p className="mt-1 text-xs text-text-muted">{meta.sub}</p>
                    </button>
                  );
                })}
              </div>
            </div>
            <div className="flex justify-end">
              <Button variant="primary" disabled={!target || busy} onClick={() => setStep(1)}>
                Continue
                <Icon.ArrowRight size={14} />
              </Button>
            </div>
          </div>
        </Card>
      )}

      {step === 1 && (
        <Card title="Pre-flight check" subtitle="SSRF, scheme, scope and intensity validation">
          <div className="space-y-3">
            <div className="rounded-md border border-bg-line bg-bg-elevated p-3 text-sm">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-xs text-text-muted">Target</span>
                  <div className="font-mono text-text-primary">{target}</div>
                </div>
                <div>
                  <span className="text-xs text-text-muted">Intensity</span>
                  <div className="font-mono text-text-primary">{intensity}</div>
                </div>
                <div>
                  <span className="text-xs text-text-muted">Engagement</span>
                  <div className="font-mono text-text-primary">
                    {engagements.data?.find((x) => x.id === engagementId)?.name ?? 'none'}
                  </div>
                </div>
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={() => setStep(0)} variant="ghost">
                Back
              </Button>
              <Button variant="primary" disabled={busy} onClick={runPreflight}>
                {busy ? 'Running…' : 'Run pre-flight'}
              </Button>
            </div>
          </div>
        </Card>
      )}

      {step === 2 && pre && (
        <div className="space-y-4">
          <Card className={pre.allowed ? 'border-status-success/40' : 'border-sev-critical/40'}>
            <div className="flex items-start gap-3">
              <div
                className={`grid h-9 w-9 shrink-0 place-items-center rounded-md ring-1 ${
                  pre.allowed
                    ? 'bg-status-success/10 text-status-success ring-status-success/30'
                    : 'bg-sev-critical/10 text-sev-critical ring-sev-critical/30'
                }`}
              >
                {pre.allowed ? <Icon.ShieldCheck size={18} /> : <Icon.X size={18} />}
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="font-display text-sm font-medium text-text-primary">
                  {pre.allowed ? 'Pre-flight passed' : 'Pre-flight blocked'}
                </h3>
                <p className="mt-0.5 text-sm text-text-muted">{pre.reason}</p>
                {pre.target_violation && (
                  <p className="mt-2 text-sm text-sev-critical">
                    {pre.target_violation}: {pre.target_violation_message}
                  </p>
                )}
                {pre.violations.length > 0 && (
                  <ul className="mt-2 list-disc pl-5 text-sm text-sev-critical">
                    {pre.violations.map((v) => (
                      <li key={v}>{v}</li>
                    ))}
                  </ul>
                )}
                {pre.needs_human_approval && (
                  <p className="mt-2 inline-flex items-center gap-1.5 text-sm text-accent-warn">
                    <Icon.Shield size={14} />
                    Human approval required before scan starts.
                  </p>
                )}
              </div>
            </div>
          </Card>

          <Card title="Scanners" subtitle={`Available for ${intensity} intensity`}>
            <div className="grid gap-2 sm:grid-cols-2">
              {SCANNERS_BY_INTENSITY[intensity].map((s) => {
                const sel = scanners.includes(s);
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
                        setScanners((cur) =>
                          e.target.checked
                            ? Array.from(new Set([...cur, s]))
                            : cur.filter((x) => x !== s)
                        )
                      }
                      className="accent-brand"
                    />
                    <div>
                      <div className="font-mono text-sm text-text-primary">{s}</div>
                    </div>
                  </label>
                );
              })}
            </div>
          </Card>

          <div className="flex gap-2">
            <Button variant="ghost" onClick={() => setStep(0)}>
              Edit target
            </Button>
            <Button
              variant="primary"
              disabled={!pre.allowed || scanners.length === 0 || busy}
              onClick={() => setStep(3)}
            >
              Continue
              <Icon.ArrowRight size={14} />
            </Button>
          </div>
        </div>
      )}

      {step === 3 && (
        <Card title="Confirm & launch">
          <dl className="grid gap-3 sm:grid-cols-2">
            <Field label="Target" value={target} mono />
            <Field label="Intensity" value={intensity} mono />
            <Field
              label="Scanners"
              value={
                <div className="flex flex-wrap gap-1">
                  {scanners.map((s) => (
                    <Chip key={s}>{s}</Chip>
                  ))}
                </div>
              }
            />
            <Field
              label="Approval"
              value={
                pre?.needs_human_approval ? (
                  <span className="text-accent-warn">required (HITL)</span>
                ) : (
                  <span className="text-status-success">not required</span>
                )
              }
            />
          </dl>
          <div className="mt-5 flex gap-2">
            <Button variant="ghost" onClick={() => setStep(2)}>
              Back
            </Button>
            <Button variant="primary" disabled={busy} onClick={submit}>
              {busy ? 'Submitting…' : 'Launch scan'}
              <Icon.Bolt size={14} />
            </Button>
          </div>
        </Card>
      )}

      {err && (
        <p className="rounded border border-sev-critical/40 bg-sev-critical/10 px-3 py-2 text-sm text-sev-critical">
          {err}
        </p>
      )}
    </div>
  );
}

function Field({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div>
      <dt className="text-2xs font-mono uppercase tracking-wider text-text-muted">{label}</dt>
      <dd className={`mt-1 text-sm text-text-primary ${mono ? 'font-mono' : ''}`}>{value}</dd>
    </div>
  );
}
