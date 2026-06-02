import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { api, type Severity } from '../lib/api';
import { Button, Card, EmptyState, Icon, PageHeader } from '../components/ui';
import { FilterPill } from './findings_explorer/FilterPill';
import { FindingsTable } from './findings_explorer/FindingsTable';

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
