'use client';

import { useMemo, useState } from 'react';
import { Virtuoso } from 'react-virtuoso';
import { useTranslations } from 'next-intl';
import {
  CheckCircle2,
  Download,
  FileJson,
  Info,
  Search,
  ShieldAlert,
  TriangleAlert,
  XCircle,
  type LucideIcon,
} from 'lucide-react';
import { FindingCard } from './FindingCard';
import { WorkspaceVerdict } from './WorkspaceVerdict';
import { useAppStore } from '@/lib/store';
import { exportReportMarkdown, exportReportJson, type Finding, type Severity } from '@/lib/api';
import { ScoreGauge } from '@/components/ui/ScoreGauge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { cn } from '@/lib/cn';

function downloadText(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

type FilterKey = 'ALL' | 'FAIL' | 'WARN' | 'PASS';
const FILTER_KEYS: Array<{
  key: FilterKey;
  icon: LucideIcon;
  i18nKey: 'all' | 'fail' | 'warn' | 'pass';
}> = [
  { key: 'ALL', icon: Info, i18nKey: 'all' },
  { key: 'FAIL', icon: XCircle, i18nKey: 'fail' },
  { key: 'WARN', icon: TriangleAlert, i18nKey: 'warn' },
  { key: 'PASS', icon: CheckCircle2, i18nKey: 'pass' },
];

export function FindingsPanel() {
  const t = useTranslations('findings.panel');
  const report = useAppStore((s) => s.currentReport);
  const selected = useAppStore((s) => s.selectedFinding);
  const setSelected = useAppStore((s) => s.setSelectedFinding);
  const openDetail = useAppStore((s) => s.openDetailFor);
  const [filter, setFilter] = useState<FilterKey>('ALL');
  const [query, setQuery] = useState('');

  const findings = useMemo(() => {
    if (!report) return [] as Finding[];
    let list =
      filter === 'ALL' ? report.findings : report.findings.filter((f) => f.severity === filter);
    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter(
        (f) =>
          f.explanation.toLowerCase().includes(q) ||
          f.rule_id.toLowerCase().includes(q) ||
          f.policy_ref.policy_id.toLowerCase().includes(q)
      );
    }
    return list;
  }, [filter, query, report]);

  const counts = useMemo(() => {
    if (!report) return { ALL: 0, FAIL: 0, WARN: 0, PASS: 0 };
    return {
      ALL: report.findings.length,
      FAIL: report.by_severity.FAIL ?? 0,
      WARN: report.by_severity.WARN ?? 0,
      PASS: report.by_severity.PASS ?? 0,
    };
  }, [report]);

  if (!report) {
    return (
      <div className="h-full bg-bg-panel-soft p-6">
        <EmptyState
          icon={ShieldAlert}
          title={t('noAnalysisTitle')}
          description={t('noAnalysisDesc')}
        />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-bg-panel-soft">
      <div className="border-b border-border bg-bg-panel/85 backdrop-blur-md sticky top-0 z-10">
        <div className="p-4">
          <div className="rounded-xl border border-border surface-elev p-4 shadow-inner-soft">
            {(() => {
              const policiesApplied = report.policies_applied ?? [];
              const chunksEvaluated = report.chunks_evaluated ?? 0;
              // Indeterminate only when INPUTS are missing (no policies / no document).
              // 0 findings on a real run = legit "clean document".
              const missingPolicies = policiesApplied.length === 0;
              const missingChunks = report.chunks_evaluated !== undefined && chunksEvaluated === 0;
              const hasEngineErrors = (report.engine_errors?.length ?? 0) > 0;
              const indeterminate = missingPolicies || missingChunks || hasEngineErrors;
              return (
                <>
                  <div className="flex items-center gap-4">
                    <ScoreGauge score={report.score} size={84} indeterminate={indeterminate} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <h2 className="text-sm font-semibold tracking-tight">
                          {t('complianceResult')}
                        </h2>
                        <span className="rounded border border-border bg-bg-canvas px-2 py-0.5 text-[10px] font-mono text-text-muted">
                          {report.report_id.slice(0, 10)}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-text-muted">
                        {indeterminate
                          ? t('indeterminate')
                          : t('summary', {
                              count: report.findings.length,
                              policies: policiesApplied.length,
                              chunks: chunksEvaluated,
                            })}
                      </p>
                      <div className="mt-3 grid grid-cols-3 gap-2">
                        <SeverityCounter severity="FAIL" count={counts.FAIL} />
                        <SeverityCounter severity="WARN" count={counts.WARN} />
                        <SeverityCounter severity="PASS" count={counts.PASS} />
                      </div>
                    </div>
                  </div>
                  {indeterminate && (
                    <div className="mt-3 rounded-md border border-status-warning/40 bg-status-warning/10 px-3 py-2 text-[11px] leading-5 text-status-warning">
                      <strong className="font-semibold">{t('indeterminateBanner')}</strong>{' '}
                      {policiesApplied.length === 0 && t('noPolicies')}
                      {chunksEvaluated === 0 && t('notParsed')}
                    </div>
                  )}
                  {(report.engine_errors?.length ?? 0) > 0 && (
                    <div className="mt-3 rounded-md border border-status-danger/40 bg-status-danger/10 px-3 py-2 text-[11px] leading-5 text-status-danger">
                      <strong className="font-semibold">
                        {t('engineErrors', {
                          count: report.engine_errors!.length,
                        })}
                      </strong>{' '}
                      {t('scoreUnreliable')}
                      <ul className="mt-1 list-disc space-y-0.5 pl-4 font-mono text-[10px]">
                        {report.engine_errors!.slice(0, 5).map((e, i) => (
                          <li key={i} className="break-all">
                            {e}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              );
            })()}
          </div>
        </div>

        <div className="px-4 pb-3">
          <WorkspaceVerdict reportId={report.report_id} findingsCount={report.findings.length} />
        </div>

        <div className="px-4 pb-3 space-y-2.5">
          <label className="flex h-9 items-center gap-2 rounded-md border border-border bg-bg-canvas px-3 ring-focus focus-within:border-status-info/50">
            <Search size={13} className="text-text-muted" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('filterPlaceholder')}
              className="min-w-0 flex-1 bg-transparent text-xs outline-none placeholder:text-text-muted"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery('')}
                className="text-[11px] text-text-muted hover:text-text-primary"
              >
                {t('clear')}
              </button>
            )}
          </label>
          <div className="flex items-center gap-1.5 overflow-x-auto">
            {FILTER_KEYS.map(({ key, icon: Icon, i18nKey }) => {
              const label = t(`filters.${i18nKey}`);
              const active = filter === key;
              const count = counts[key];
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => setFilter(key)}
                  className={cn(
                    'inline-flex h-7 items-center gap-1.5 rounded-full border px-2.5 text-[11px] font-medium transition-colors',
                    active
                      ? 'border-status-info/40 bg-status-info/15 text-status-info'
                      : 'border-border bg-bg-canvas text-text-secondary hover:bg-bg-panel-elev hover:text-text-primary'
                  )}
                >
                  <Icon size={12} />
                  {label}
                  <span
                    className={cn(
                      'rounded-full px-1.5 py-px text-[10px] font-mono',
                      active ? 'bg-status-info/20' : 'bg-bg-panel text-text-muted'
                    )}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
            <span className="ml-auto text-[11px] text-text-muted whitespace-nowrap">
              {t('shown', { count: findings.length })}
            </span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-hidden py-2">
        {findings.length === 0 ? (
          <div className="px-4 py-8">
            <EmptyState icon={Search} title={t('noMatchTitle')} description={t('noMatchDesc')} />
          </div>
        ) : (
          <Virtuoso
            data={findings}
            itemContent={(_, finding) => (
              <div className="px-4">
                <FindingCard
                  finding={finding}
                  selected={selected?.id === finding.id}
                  onSelect={openDetail}
                  onViewInDoc={setSelected}
                />
              </div>
            )}
          />
        )}
      </div>

      <div className="p-4 border-t border-border bg-bg-panel/95 backdrop-blur-md sticky bottom-0 flex gap-2">
        <Button
          variant="primary"
          size="lg"
          className="flex-1"
          onClick={async () => {
            const md = await exportReportMarkdown(report.doc_id);
            downloadText(`${report.report_id}.md`, md, 'text/markdown');
          }}
        >
          <Download size={15} /> {t('exportSigned')}
        </Button>
        <Button
          variant="outline"
          size="lg"
          onClick={async () => {
            const j = await exportReportJson(report.doc_id);
            downloadText(
              `${report.report_id}.json`,
              JSON.stringify(j, null, 2),
              'application/json'
            );
          }}
        >
          <FileJson size={15} /> {t('exportJson')}
        </Button>
      </div>
    </div>
  );
}

function SeverityCounter({ severity, count }: { severity: Severity; count: number }) {
  const config = {
    FAIL: {
      icon: XCircle,
      cls: 'text-status-danger bg-status-danger/10 border-status-danger/30',
    },
    WARN: {
      icon: TriangleAlert,
      cls: 'text-status-warning bg-status-warning/10 border-status-warning/30',
    },
    PASS: {
      icon: CheckCircle2,
      cls: 'text-status-success bg-status-success/10 border-status-success/30',
    },
    INFO: {
      icon: ShieldAlert,
      cls: 'text-status-info bg-status-info/10 border-status-info/30',
    },
  }[severity];
  const Icon = config.icon;

  return (
    <div className={cn('rounded-md border px-2 py-2', config.cls)}>
      <div className="flex items-center gap-1.5 text-[10px] font-semibold tracking-wide">
        <Icon size={12} />
        {severity}
      </div>
      <div className="mt-1 text-xl font-semibold tabular-nums leading-none">{count}</div>
    </div>
  );
}
