'use client';

import {
  Copy,
  Download,
  Edit3,
  ListChecks,
  Plus,
  Power,
  PowerOff,
  Scale,
  Sparkles,
  Trash2,
} from 'lucide-react';

import { useTranslations } from 'next-intl';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import type { PolicyRow, RuleRow } from '@/lib/api';
import { cn } from '@/lib/cn';

import { Stat } from './PolicyBits';

export interface PolicyDetailPaneProps {
  selected: PolicyRow | null;
  rulesData: RuleRow[] | undefined;
  rulesLoading: boolean;
  activePending: boolean;
  onToggleActive: () => void;
  onEdit: () => void;
  onCloneRequest: () => void;
  onExport: () => void;
  onDeletePolicy: () => void;
  onCreateRule: () => void;
  onSuggestRules: () => void;
  onEditRule: (r: RuleRow) => void;
  onDeleteRule: (r: RuleRow) => void;
}

export function PolicyDetailPane({
  selected,
  rulesData,
  rulesLoading,
  activePending,
  onToggleActive,
  onEdit,
  onCloneRequest,
  onExport,
  onDeletePolicy,
  onCreateRule,
  onSuggestRules,
  onEditRule,
  onDeleteRule,
}: PolicyDetailPaneProps) {
  const t = useTranslations('policies.detail');
  if (!selected) {
    return (
      <section className="overflow-auto bg-bg-canvas p-6">
        <EmptyState icon={Scale} title={t('noSelectionTitle')} description={t('noSelectionDesc')} />
      </section>
    );
  }

  return (
    <section className="overflow-auto bg-bg-canvas p-6">
      <div className="mx-auto max-w-5xl">
        <Card className="mb-5 p-5">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-text-muted">
                {t('eyebrow')}
              </div>
              <h2 className="mt-2 text-xl font-semibold tracking-tight text-text-primary">
                {selected.title}
              </h2>
              <p className="mt-2 font-mono text-xs text-text-muted">
                {selected.id}@{selected.version} · {t('scope')} {selected.scope}
              </p>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <Stat label={t('statRules')} value={String(selected.rule_count)} />
              <Stat label={t('statLang')} value={selected.lang.toUpperCase()} />
              <Stat
                label={t('statStatus')}
                value={selected.active ? t('statusActive') : t('statusDraft')}
              />
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            <Button
              size="sm"
              variant={selected.active ? 'outline' : 'primary'}
              onClick={onToggleActive}
              disabled={activePending}
            >
              {selected.active ? <PowerOff size={13} /> : <Power size={13} />}
              {selected.active ? t('deactivate') : t('activate')}
            </Button>
            <Button size="sm" variant="secondary" onClick={onEdit}>
              <Edit3 size={13} /> {t('edit')}
            </Button>
            <Button size="sm" variant="secondary" onClick={onCloneRequest}>
              <Copy size={13} /> {t('cloneVersion')}
            </Button>
            <Button size="sm" variant="outline" onClick={onExport}>
              <Download size={13} /> {t('exportYaml')}
            </Button>
            <Button size="sm" variant="danger" onClick={onDeletePolicy} className="ml-auto">
              <Trash2 size={13} /> {t('delete')}
            </Button>
          </div>
        </Card>

        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <h3 className="flex items-center gap-2 text-sm font-semibold">
              <ListChecks size={15} className="text-status-info" />
              {t('rules')}
            </h3>
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-muted">
                {t('loaded', { count: rulesData?.length ?? 0 })}
              </span>
              <Button size="sm" variant="secondary" onClick={onSuggestRules}>
                <Sparkles size={13} /> {t('suggestRules')}
              </Button>
              <Button size="sm" variant="primary" onClick={onCreateRule}>
                <Plus size={13} /> {t('newRule')}
              </Button>
            </div>
          </div>

          {rulesLoading && (
            <div className="p-4 space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-20" />
              ))}
            </div>
          )}

          {!rulesLoading && (rulesData?.length ?? 0) === 0 && (
            <div className="p-6">
              <EmptyState
                icon={ListChecks}
                title={t('noRulesTitle')}
                description={t('noRulesDesc')}
              />
            </div>
          )}

          <div className="divide-y divide-border">
            {rulesData?.map((r) => (
              <div key={r.id} className="p-4">
                <div className="mb-3 flex items-center gap-2">
                  <span className="font-mono text-xs text-text-secondary">{r.id}</span>
                  <span className="rounded border border-border bg-bg-canvas px-2 py-0.5 text-[10px] uppercase text-text-muted">
                    {r.rule_type}
                  </span>
                  <span
                    className={cn(
                      'rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase',
                      r.severity === 'fail' &&
                        'border-status-danger/30 bg-status-danger/10 text-status-danger',
                      r.severity === 'warn' &&
                        'border-status-warning/30 bg-status-warning/10 text-status-warning',
                      r.severity === 'info' &&
                        'border-status-info/30 bg-status-info/10 text-status-info'
                    )}
                  >
                    {r.severity}
                  </span>
                  <div className="ml-auto flex gap-1">
                    <Button size="sm" variant="ghost" onClick={() => onEditRule(r)}>
                      <Edit3 size={12} /> {t('ruleEdit')}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-status-danger hover:text-status-danger"
                      onClick={() => onDeleteRule(r)}
                    >
                      <Trash2 size={12} /> {t('ruleDelete')}
                    </Button>
                  </div>
                </div>
                <pre className="rounded-md border border-border bg-bg-canvas p-3 font-mono text-[11px] leading-5 text-text-secondary whitespace-pre-wrap">
                  {r.excerpt}
                </pre>
                {r.matcher && (
                  <div className="mt-2 rounded-md border border-dashed border-border bg-bg-panel-soft p-2 font-mono text-[10px] text-text-muted">
                    {t('matcher')} {r.matcher}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>
    </section>
  );
}
