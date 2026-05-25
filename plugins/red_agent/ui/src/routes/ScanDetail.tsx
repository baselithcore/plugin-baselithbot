import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, openScanStream, type Finding, type Severity } from '../lib/api';
import {
  Button,
  Card,
  Chip,
  ConfirmDialog,
  EmptyState,
  FindingDetailModal,
  Icon,
  MenuDivider,
  MenuHeader,
  MenuItem,
  PageHeader,
  Popover,
  SeverityBadge,
  StatusBadge,
} from '../components/ui';

const SEVERITY_ORDER: Severity[] = ['critical', 'high', 'medium', 'low', 'info'];

export function ScanDetail() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const [live, setLive] = useState<Finding[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [selected, setSelected] = useState<Finding | null>(null);

  const remove = useMutation({
    mutationFn: () => api.deleteScan(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['scans'] });
      nav('/scans');
    },
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ['scan', id],
    queryFn: () => api.getScan(id),
    refetchInterval: 2000,
    enabled: Boolean(id),
  });

  useEffect(() => {
    if (!id) return;
    const ws = openScanStream(id);
    ws.onmessage = (e) => {
      const frame = JSON.parse(e.data);
      if (frame.type === 'finding') setLive((p) => [frame.finding, ...p]);
      if (frame.type === 'status') setStatus(frame.status);
    };
    return () => ws.close();
  }, [id]);

  const findings = live.length > 0 ? live : (data?.findings ?? []);
  const effectiveStatus = status ?? data?.status ?? 'queued';
  const awaitingApproval = effectiveStatus === 'awaiting_approval';

  const sevCounts = useMemo(() => {
    const c: Record<Severity, number> = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    for (const x of findings) c[x.severity]++;
    return c;
  }, [findings]);

  const sortedFindings = useMemo(() => {
    return [...findings].sort((a, b) => {
      const ai = SEVERITY_ORDER.indexOf(a.severity);
      const bi = SEVERITY_ORDER.indexOf(b.severity);
      if (ai !== bi) return ai - bi;
      return (b.cvss_score ?? 0) - (a.cvss_score ?? 0);
    });
  }, [findings]);

  async function approve() {
    setBusy(true);
    try {
      await api.approveScan(id);
      setStatus('running');
    } catch (e) {
      alert(`approve failed: ${String(e)}`);
    } finally {
      setBusy(false);
    }
  }
  async function reject() {
    setBusy(true);
    try {
      await api.rejectScan(id);
      setStatus('cancelled');
    } catch (e) {
      alert(`reject failed: ${String(e)}`);
    } finally {
      setBusy(false);
    }
  }
  async function cancel() {
    if (!window.confirm('Stop this scan? In-flight scanners will be aborted.')) return;
    setBusy(true);
    try {
      await api.cancelScan(id);
      setStatus('cancelled');
    } catch (e) {
      alert(`cancel failed: ${String(e)}`);
    } finally {
      setBusy(false);
    }
  }

  const cancellable = ['queued', 'running', 'awaiting_approval'].includes(effectiveStatus);
  const deletable = ['completed', 'failed', 'cancelled'].includes(effectiveStatus);

  if (isLoading) {
    return (
      <div className="grid place-items-center py-20 text-sm text-text-muted">
        <span className="font-mono">Loading scan…</span>
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
  if (!data) return null;

  const duration = data.finished_at
    ? Math.round(
        (new Date(data.finished_at).getTime() - new Date(data.started_at).getTime()) / 1000
      )
    : Math.round((Date.now() - new Date(data.started_at).getTime()) / 1000);

  return (
    <div className="space-y-6">
      <PageHeader
        title={
          <span className="flex items-center gap-3">
            <span>Scan</span>
            <span className="font-mono text-base font-normal text-text-muted">
              {id.slice(0, 8)}
            </span>
          </span>
        }
        breadcrumbs={[{ label: 'Scans' }, { label: id.slice(0, 8) }]}
        meta={
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={effectiveStatus} />
            <Chip>
              <Icon.Clock size={11} /> {duration}s
            </Chip>
            <Chip>
              <Icon.Activity size={11} /> {findings.length} findings
            </Chip>
          </div>
        }
        actions={
          <div className="flex items-center gap-2">
            {cancellable && (
              <Button variant="danger" size="sm" onClick={cancel} disabled={busy}>
                <Icon.X size={12} />
                Stop scan
              </Button>
            )}
            {deletable && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setConfirmDelete(true)}
                disabled={remove.isPending}
                className="text-sev-critical hover:bg-sev-critical/10"
              >
                <Icon.Trash size={12} />
                Delete
              </Button>
            )}
            <Popover
              align="right"
              width={260}
              trigger={
                <button type="button" className="ra-btn ra-btn-secondary">
                  <Icon.Download size={14} />
                  Export
                  <Icon.ChevronDown size={12} />
                </button>
              }
            >
              <MenuHeader>Reports</MenuHeader>
              <MenuItem
                icon={<Icon.Download size={14} />}
                label="SARIF (GitHub / Defect Dojo)"
                description="Static analysis results format"
                href={`/red-agent/reports/${id}/sarif`}
              />
              <MenuItem
                icon={<Icon.Download size={14} />}
                label="OCSF Vulnerability Findings"
                description="Splunk · Sentinel · Chronicle · Panther"
                href={`/red-agent/reports/${id}/ocsf`}
              />
              <MenuItem
                icon={<Icon.Download size={14} />}
                label="Sigma rules (ZIP)"
                description="One YAML per finding with detection_guidance"
                href={`/red-agent/reports/${id}/sigma.zip`}
              />
              <MenuDivider />
              <MenuHeader>Compliance coverage</MenuHeader>
              <MenuItem
                label="All frameworks"
                description="Full CWE → control mapping"
                href={`/red-agent/reports/${id}/compliance`}
              />
              <MenuItem label="CIS" href={`/red-agent/reports/${id}/compliance?framework=cis`} />
              <MenuItem
                label="PCI DSS 4.0"
                href={`/red-agent/reports/${id}/compliance?framework=pci_dss_4`}
              />
              <MenuItem
                label="NIST 800-53"
                href={`/red-agent/reports/${id}/compliance?framework=nist_800_53`}
              />
              <MenuItem
                label="ISO 27001"
                href={`/red-agent/reports/${id}/compliance?framework=iso27001`}
              />
              <MenuItem label="SOC 2" href={`/red-agent/reports/${id}/compliance?framework=soc2`} />
            </Popover>
          </div>
        }
      />

      <ConfirmDialog
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        onConfirm={() => remove.mutateAsync()}
        title="Delete scan permanently?"
        description={
          <>
            Run <span className="font-mono text-text-primary">{id.slice(0, 8)}</span> and all of its
            findings will be removed.
          </>
        }
        consequences={[
          'All findings discovered in this run will be deleted.',
          'Audit log entries are preserved for compliance.',
          'This action cannot be undone.',
        ]}
        acknowledgement="I understand this run and its findings will be permanently deleted."
        confirmLabel="Delete forever"
        tone="danger"
        busy={remove.isPending}
      />

      {awaitingApproval && (
        <Card className="border-accent-warn/40">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-accent-warn/10 text-accent-warn ring-1 ring-accent-warn/30">
                <Icon.Shield size={18} />
              </div>
              <div>
                <h3 className="font-display text-sm font-medium text-text-primary">
                  Human-in-the-loop approval required
                </h3>
                <p className="mt-0.5 text-sm text-text-muted">
                  Active or intrusive scan — must be authorized before scanners run.
                </p>
              </div>
            </div>
            <div className="flex gap-2 sm:shrink-0">
              <Button variant="primary" onClick={approve} disabled={busy}>
                <Icon.Check size={14} />
                Approve & launch
              </Button>
              <Button variant="danger" onClick={reject} disabled={busy}>
                <Icon.X size={14} />
                Reject
              </Button>
            </div>
          </div>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {SEVERITY_ORDER.map((sev) => (
          <div key={sev} className="ra-card px-4 py-3">
            <div className="flex items-center justify-between">
              <SeverityBadge severity={sev} full />
              <span className="font-display text-2xl font-medium tabular-nums text-text-primary">
                {sevCounts[sev]}
              </span>
            </div>
          </div>
        ))}
      </div>

      <Card
        title="Findings"
        subtitle={
          live.length > 0
            ? `Streaming live · ${findings.length} discovered`
            : effectiveStatus === 'running' || effectiveStatus === 'queued'
              ? `${findings.length} so far · scanners run in parallel, fast ones report first`
              : `${findings.length} from completed run`
        }
        action={live.length > 0 ? <Chip tone="brand">live</Chip> : null}
        padded={false}
      >
        {sortedFindings.length === 0 ? (
          <EmptyState
            icon={<Icon.ShieldCheck size={20} />}
            title="No findings yet"
            description={
              effectiveStatus === 'running' || effectiveStatus === 'queued'
                ? 'Scanners running in parallel — fast ones publish findings first.'
                : effectiveStatus === 'failed'
                  ? 'Scan failed before producing findings. Check error and audit log.'
                  : effectiveStatus === 'cancelled'
                    ? 'Scan cancelled before producing findings.'
                    : 'Scan completed without surfacing any issues.'
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="ra-table">
              <thead>
                <tr>
                  <th className="w-24">Severity</th>
                  <th>Finding</th>
                  <th className="w-28">Scanner</th>
                  <th className="w-28">CVE</th>
                  <th className="w-20 text-right">CVSS</th>
                  <th className="w-20 text-right">Risk</th>
                  <th className="w-24">CWE</th>
                </tr>
              </thead>
              <tbody>
                {sortedFindings.map((x) => (
                  <tr
                    key={x.id}
                    onClick={() => setSelected(x)}
                    className="cursor-pointer transition-colors hover:bg-bg-hover/50"
                  >
                    <td>
                      <SeverityBadge severity={x.severity} full />
                    </td>
                    <td>
                      <div className="min-w-0">
                        <div className="truncate font-medium text-text-primary">{x.title}</div>
                        <div className="mt-0.5 truncate font-mono text-xs text-text-muted">
                          {x.endpoint ?? x.target}
                        </div>
                      </div>
                    </td>
                    <td>
                      <Chip>{x.scanner}</Chip>
                    </td>
                    <td className="font-mono text-xs text-text-secondary">{x.cve ?? '—'}</td>
                    <td className="text-right font-mono tabular-nums text-text-secondary">
                      {x.cvss_score ?? '—'}
                    </td>
                    <td className="text-right font-mono tabular-nums text-text-secondary">
                      {x.risk_score != null && Number.isFinite(x.risk_score)
                        ? x.risk_score.toFixed(1)
                        : '—'}
                    </td>
                    <td className="font-mono text-xs text-text-secondary">{x.cwe ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <FindingDetailModal
        finding={selected}
        open={selected !== null}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}
