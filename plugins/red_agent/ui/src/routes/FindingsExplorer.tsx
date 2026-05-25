import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { api, type Finding, type Severity } from '../lib/api';
import {
  Button,
  Card,
  Chip,
  EmptyState,
  FindingDetailModal,
  Icon,
  PageHeader,
  SeverityBadge,
} from '../components/ui';

const SEVERITIES: Severity[] = ['critical', 'high', 'medium', 'low', 'info'];
const SEV_LABEL: Record<Severity, string> = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  info: 'Info',
};
const SEV_COLOR: Record<Severity, string> = {
  critical: '#ff3860',
  high: '#fb7c1d',
  medium: '#f59e0b',
  low: '#2dd4bf',
  info: '#4cc9f0',
};
const SEV_BORDER: Record<Severity, string> = {
  critical: 'border-sev-critical/60',
  high: 'border-sev-high/60',
  medium: 'border-sev-medium/60',
  low: 'border-sev-low/60',
  info: 'border-sev-info/60',
};

export function FindingsExplorer() {
  const [params, setParams] = useSearchParams();
  const [severity, setSeverity] = useState<Severity | ''>('');
  const [scanner, setScanner] = useState('');
  const [target, setTarget] = useState(params.get('target') ?? '');
  const [cwe, setCwe] = useState('');
  const [groupBy, setGroupBy] = useState<'' | 'severity' | 'scanner' | 'target'>('');

  const filters = { severity, scanner, target, cwe };

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['findings', filters],
    queryFn: () =>
      api.listFindings({
        severity: severity || undefined,
        scanner: scanner || undefined,
        target: target || undefined,
        cwe: cwe || undefined,
        limit: 500,
      }),
  });

  const sevCounts = useMemo(() => {
    const c: Record<Severity, number> = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    for (const x of data ?? []) c[x.severity]++;
    return c;
  }, [data]);

  function clearFilters() {
    setSeverity('');
    setScanner('');
    setTarget('');
    setCwe('');
    setGroupBy('');
    setParams({}, { replace: true });
  }

  const activeChips: { key: string; label: string; onRemove: () => void }[] = [];
  if (severity) {
    activeChips.push({
      key: 'sev',
      label: `Severity: ${SEV_LABEL[severity]}`,
      onRemove: () => setSeverity(''),
    });
  }
  if (scanner) {
    activeChips.push({ key: 'sc', label: `Scanner: ${scanner}`, onRemove: () => setScanner('') });
  }
  if (target) {
    activeChips.push({
      key: 't',
      label: `Target: ${target}`,
      onRemove: () => {
        setTarget('');
        setParams({}, { replace: true });
      },
    });
  }
  if (cwe) {
    activeChips.push({ key: 'cwe', label: `CWE: ${cwe}`, onRemove: () => setCwe('') });
  }

  const grouped = useMemo(() => {
    if (!groupBy || !data) return null;
    const map = new Map<string, typeof data>();
    for (const x of data) {
      const k =
        groupBy === 'severity'
          ? x.severity
          : groupBy === 'scanner'
            ? x.scanner
            : (x.endpoint ?? x.target);
      if (!map.has(k)) map.set(k, []);
      map.get(k)!.push(x);
    }
    return Array.from(map.entries()).sort((a, b) => b[1].length - a[1].length);
  }, [data, groupBy]);

  const total = data?.length ?? 0;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Findings"
        description="Faceted search across all completed scans."
        breadcrumbs={[{ label: 'Workspace' }, { label: 'Findings' }]}
        actions={
          <>
            <Button variant="secondary" onClick={() => refetch()} disabled={isFetching}>
              <Icon.Refresh size={14} />
              Refresh
            </Button>
            <Button variant="ghost" title="Save view">
              <Icon.Save size={14} />
              Save view
            </Button>
          </>
        }
      />

      {/* Severity facets row */}
      <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {SEVERITIES.map((s) => (
          <button
            key={s}
            onClick={() => setSeverity((cur) => (cur === s ? '' : s))}
            className={`group rounded-md border bg-bg-card px-3 py-2.5 text-left transition-colors ${
              severity === s ? SEV_BORDER[s] : 'border-bg-line hover:border-bg-line-strong'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className={`sev-pill ${s}`}>{SEV_LABEL[s]}</span>
              <span className="font-display text-xl font-medium tabular-nums text-text-primary">
                {sevCounts[s]}
              </span>
            </div>
            <div className="mt-1.5 h-1 overflow-hidden rounded bg-bg-overlay">
              <div
                className="h-full rounded"
                style={{
                  width: total > 0 ? `${(sevCounts[s] / total) * 100}%` : '0%',
                  background: SEV_COLOR[s],
                }}
              />
            </div>
          </button>
        ))}
      </div>

      <Card padded={false}>
        {/* Filter toolbar */}
        <div className="flex flex-wrap items-center gap-2 border-b border-bg-line/60 px-4 py-2.5">
          <div className="relative flex-1 min-w-[220px] max-w-md">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">
              <Icon.Search size={13} />
            </span>
            <input
              placeholder="Search target, endpoint, CVE…"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              className="ra-input pl-9 h-8 text-sm"
            />
          </div>
          <FilterPill
            label="Scanner"
            value={scanner}
            onClear={() => setScanner('')}
            renderInput={() => (
              <input
                placeholder="nmap, nuclei, zap…"
                value={scanner}
                onChange={(e) => setScanner(e.target.value)}
                className="ra-input h-7 text-xs"
                autoFocus
              />
            )}
          />
          <FilterPill
            label="CWE"
            value={cwe}
            onClear={() => setCwe('')}
            renderInput={() => (
              <input
                placeholder="CWE-79"
                value={cwe}
                onChange={(e) => setCwe(e.target.value)}
                className="ra-input h-7 text-xs"
                autoFocus
              />
            )}
          />
          <FilterPill
            label="Severity"
            value={severity ? SEV_LABEL[severity] : ''}
            onClear={() => setSeverity('')}
            renderInput={() => (
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value as Severity | '')}
                className="ra-select h-7 text-xs w-32"
                autoFocus
              >
                <option value="">All</option>
                {SEVERITIES.map((s) => (
                  <option key={s} value={s}>
                    {SEV_LABEL[s]}
                  </option>
                ))}
              </select>
            )}
          />
          <button
            type="button"
            className="inline-flex h-7 items-center gap-1 rounded border border-dashed border-bg-line-strong px-2 text-xs text-text-muted transition-colors hover:border-brand/40 hover:text-text-secondary"
          >
            <Icon.Plus size={11} />
            Filter
          </button>
          {activeChips.length > 0 && (
            <button
              type="button"
              onClick={clearFilters}
              className="text-xs font-mono text-text-muted transition-colors hover:text-brand"
            >
              Reset
            </button>
          )}
          <div className="ml-auto flex items-center gap-3">
            <span className="text-2xs font-mono uppercase tracking-wider text-text-muted">
              Group By
            </span>
            <select
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value as typeof groupBy)}
              className="ra-select h-7 w-32 text-xs"
            >
              <option value="">Select…</option>
              <option value="severity">Severity</option>
              <option value="scanner">Scanner</option>
              <option value="target">Target</option>
            </select>
          </div>
        </div>

        {/* Active filter chips */}
        {activeChips.length > 0 && (
          <div className="flex flex-wrap gap-1.5 border-b border-bg-line/60 px-4 py-2">
            {activeChips.map((c) => (
              <span
                key={c.key}
                className="inline-flex items-center gap-1.5 rounded-full bg-brand/10 px-2.5 py-0.5 text-2xs font-mono text-brand ring-1 ring-brand/30"
              >
                {c.label}
                <button
                  type="button"
                  onClick={c.onRemove}
                  className="grid h-3.5 w-3.5 place-items-center rounded-full hover:bg-brand/20"
                  aria-label={`Remove ${c.label}`}
                >
                  <Icon.X size={9} />
                </button>
              </span>
            ))}
          </div>
        )}

        <div className="flex items-center justify-between border-b border-bg-line/60 px-4 py-2 text-2xs font-mono uppercase tracking-wider text-text-muted">
          <span>
            <span className="tabular-nums text-text-primary">{total}</span> findings
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              className="grid h-6 w-6 place-items-center rounded text-text-muted hover:bg-bg-overlay hover:text-text-primary"
              title="Sort"
            >
              <Icon.Sliders size={12} />
            </button>
            <button
              type="button"
              className="grid h-6 w-6 place-items-center rounded text-text-muted hover:bg-bg-overlay hover:text-text-primary"
              title="Export"
            >
              <Icon.Download size={12} />
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="grid place-items-center py-16 text-sm text-text-muted">
            <span className="font-mono">Loading findings…</span>
          </div>
        ) : error ? (
          <div className="m-4 rounded border border-sev-critical/40 bg-sev-critical/10 p-3 text-sm text-sev-critical">
            {String(error)}
          </div>
        ) : (data ?? []).length === 0 ? (
          <EmptyState
            icon={<Icon.Findings size={20} />}
            title="No findings match"
            description={
              activeChips.length > 0
                ? 'Try widening filters or clearing them.'
                : 'Run a scan to populate findings.'
            }
            action={
              activeChips.length > 0 ? (
                <Button onClick={clearFilters}>Clear filters</Button>
              ) : (
                <Link to="/scans/new" className="ra-btn ra-btn-primary">
                  <Icon.Plus size={14} />
                  Run scan
                </Link>
              )
            }
          />
        ) : grouped ? (
          <div className="divide-y divide-bg-line/40">
            {grouped.map(([k, items]) => (
              <details key={k} open className="group">
                <summary className="flex cursor-pointer items-center justify-between gap-3 bg-bg-elevated/40 px-4 py-2 transition-colors hover:bg-bg-hover/50">
                  <div className="flex items-center gap-2">
                    <Icon.ChevronRight
                      size={12}
                      className="text-text-muted transition-transform group-open:rotate-90"
                    />
                    <span className="text-sm font-medium text-text-primary capitalize">{k}</span>
                    <span className="text-xs text-text-muted">·</span>
                    <span className="text-xs text-text-muted">{items.length}</span>
                  </div>
                </summary>
                <FindingsTable items={items} />
              </details>
            ))}
          </div>
        ) : (
          <FindingsTable items={data ?? []} />
        )}
      </Card>
    </div>
  );
}

function FilterPill({
  label,
  value,
  onClear,
  renderInput,
}: {
  label: string;
  value: string;
  onClear: () => void;
  renderInput: () => React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`inline-flex h-7 items-center gap-1.5 rounded border px-2 text-xs transition-colors ${
          value
            ? 'border-brand/50 bg-brand/10 text-brand'
            : 'border-bg-line bg-bg-elevated text-text-secondary hover:border-bg-line-strong'
        }`}
      >
        <Icon.Filter2 size={11} />
        <span>
          {label}
          {value && <span className="ml-1 font-mono text-2xs">: {value}</span>}
        </span>
        {value ? (
          <span
            role="button"
            tabIndex={0}
            onClick={(e) => {
              e.stopPropagation();
              onClear();
            }}
            className="ml-0.5 grid h-3.5 w-3.5 place-items-center rounded-full hover:bg-brand/20"
          >
            <Icon.X size={9} />
          </span>
        ) : (
          <Icon.ChevronDown size={11} className="text-text-muted" />
        )}
      </button>
      {open && (
        <div className="absolute left-0 top-9 z-30 min-w-[200px] rounded-md border border-bg-line bg-bg-elevated p-2 shadow-elevated">
          {renderInput()}
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="mt-2 w-full rounded bg-brand/10 py-1 text-xs font-medium text-brand hover:bg-brand/20"
          >
            Apply
          </button>
        </div>
      )}
    </div>
  );
}

function FindingsTable({ items }: { items: Finding[] }) {
  const [selected, setSelected] = useState<Finding | null>(null);
  return (
    <div className="overflow-x-auto">
      <table className="ra-table">
        <thead>
          <tr>
            <th className="w-24">Severity</th>
            <th>Issue</th>
            <th className="w-28">Scanner</th>
            <th className="w-28">CVE</th>
            <th className="w-20 text-right">CVSS</th>
            <th className="w-20 text-right">Risk</th>
            <th className="w-44">Target</th>
            <th className="w-32">Discovered</th>
          </tr>
        </thead>
        <tbody>
          {items.map((x) => (
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
                  {x.description && (
                    <div className="mt-0.5 truncate text-xs text-text-muted">{x.description}</div>
                  )}
                  {(x.controls ?? []).length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {x.controls.slice(0, 3).map((c) => (
                        <span
                          key={c}
                          className="rounded border border-status-success/30 bg-status-success/10 px-1.5 py-0.5 text-2xs font-mono text-status-success"
                        >
                          {c}
                        </span>
                      ))}
                      {x.controls.length > 3 && (
                        <span className="text-2xs font-mono text-text-muted">
                          +{x.controls.length - 3}
                        </span>
                      )}
                    </div>
                  )}
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
              <td className="truncate font-mono text-xs text-text-secondary">
                {x.endpoint ?? x.target}
              </td>
              <td className="font-mono text-xs text-text-muted">
                {new Date(x.discovered_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <FindingDetailModal
        finding={selected}
        open={selected !== null}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}
