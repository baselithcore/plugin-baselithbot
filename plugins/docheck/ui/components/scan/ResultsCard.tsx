'use client';

import { useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { ChevronRight, CheckCircle2, Gauge, ListChecks, Scale, Sparkles } from 'lucide-react';
import type { Finding, Report } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { SeverityBadge } from '@/components/ui/badge';
import { useAppStore } from '@/lib/store';
import type { ScanProfile } from './types';

interface Props {
  report: Report | null;
  findings: Finding[];
  profile: ScanProfile;
  phase: string;
}

export function ResultsCard({ report, findings, profile, phase }: Props) {
  const t = useTranslations('scan.results');
  const grouped = useMemo(() => {
    if (!profile.groupByPolicy) return null;
    const m = new Map<string, Finding[]>();
    for (const f of findings) {
      const key = f.policy_ref?.policy_id || 'unscoped';
      const arr = m.get(key) ?? [];
      arr.push(f);
      m.set(key, arr);
    }
    return Array.from(m.entries());
  }, [findings, profile.groupByPolicy]);

  if (!report) return null;

  return (
    <Card>
      <CardContent className="pt-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <ListChecks size={14} className="text-status-info" />
            <h3 className="text-sm font-semibold">{t('title')}</h3>
            <span className="font-mono text-[10px] text-text-muted">
              {findings.length} / {report.findings.length}
            </span>
          </div>
          <div className="text-[10px] text-text-muted flex items-center gap-3">
            <span className="inline-flex items-center gap-1">
              <Gauge size={10} />
              {t('scoreLabel', { score: report.score })}
            </span>
            <span>·</span>
            <span>
              {t('stats', {
                policies: report.policies_applied?.length ?? 0,
                chunks: report.chunks_evaluated ?? 0,
              })}
            </span>
          </div>
        </div>

        {phase === 'analyzing' ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-14" />
            ))}
          </div>
        ) : findings.length === 0 ? (
          <div className="rounded-md border border-border bg-bg-panel-soft p-6 text-center">
            <CheckCircle2 size={20} className="mx-auto text-status-success mb-2" />
            <div className="text-sm font-medium">{t('noMatch')}</div>
            <div className="mt-1 text-[11px] text-text-muted">{t('lower')}</div>
          </div>
        ) : grouped ? (
          <div className="space-y-4">
            {grouped.map(([pid, items]) => (
              <div key={pid}>
                <div className="flex items-center gap-2 mb-2 text-[11px] font-mono text-text-muted">
                  <Scale size={11} />
                  {pid}
                  <span className="text-text-muted">· {items.length}</span>
                </div>
                <div className="space-y-2">
                  {items.map((f) => (
                    <FindingRow key={f.id} f={f} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {findings.map((f) => (
              <FindingRow key={f.id} f={f} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function FindingRow({ f }: { f: Finding }) {
  const t = useTranslations('scan.results');
  const openDetailFor = useAppStore((s) => s.openDetailFor);
  return (
    <button
      type="button"
      onClick={() => openDetailFor(f)}
      aria-label={t('openDetail', { ruleId: f.rule_id })}
      className="group w-full text-left rounded-md border border-border bg-bg-canvas p-3 hover:border-status-info/50 hover:bg-bg-panel-elev/40 transition-colors ring-focus"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <SeverityBadge severity={f.severity} />
          <span className="font-mono text-[10px] text-text-muted truncate">{f.rule_id}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="font-mono text-[10px] text-text-muted">
            {t('confidence', { pct: (f.confidence * 100).toFixed(0) })}
          </span>
          <ChevronRight
            size={13}
            className="text-text-muted group-hover:text-status-info transition-colors"
          />
        </div>
      </div>
      <p className="mt-2 text-xs leading-5 text-text-secondary">{f.explanation}</p>
      {f.suggestion && (
        <div className="mt-2 flex items-start gap-1.5 text-[11px] text-status-info">
          <Sparkles size={11} className="mt-0.5 shrink-0" />
          <span className="line-clamp-2">{f.suggestion}</span>
        </div>
      )}
      {f.policy_ref?.excerpt && (
        <div className="mt-2 rounded border-l-2 border-status-info/40 bg-bg-panel-soft px-2.5 py-1.5 text-[11px] text-text-muted italic line-clamp-2">
          “{f.policy_ref.excerpt}”
        </div>
      )}
      <div className="mt-2 text-[10px] text-text-muted opacity-0 group-hover:opacity-100 transition-opacity">
        {t('clickHint')}
      </div>
    </button>
  );
}
