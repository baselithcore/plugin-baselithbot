'use client';

import { useQuery } from '@tanstack/react-query';
import { ListChecks } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import { listRules, type PolicyRow } from '@/lib/api';
import { cn } from '@/lib/cn';

import { PolicySwitch } from './PolicyToggleBoard';

function useScopeLabel() {
  const t = useTranslations('policies.scope');
  return (s: PolicyRow['scope']): string => {
    switch (s) {
      case 'global_default':
        return t('global_default');
      case 'eu':
        return t('eu');
      case 'world':
        return t('world');
      case 'custom':
        return t('custom');
    }
  };
}

export interface PolicyManagerDetailProps {
  open: boolean;
  selectedRow: PolicyRow | null;
  selected: string[];
  onToggle: (id: string) => void;
}

export function PolicyManagerDetail({
  open,
  selectedRow,
  selected,
  onToggle,
}: PolicyManagerDetailProps) {
  const t = useTranslations('policies.managerDetail');
  const tPolicies = useTranslations('policies');
  const scopeLabel = useScopeLabel();
  const rules = useQuery({
    queryKey: ['rules', selectedRow?.id, selectedRow?.version],
    queryFn: () => listRules(selectedRow!.id, selectedRow!.version),
    enabled: open && !!selectedRow,
  });

  if (!selectedRow) {
    return (
      <section className="min-h-0 overflow-auto bg-bg-canvas p-5">
        <EmptyState
          icon={ListChecks}
          title={t('noSelectionTitle')}
          description={t('noSelectionDesc')}
        />
      </section>
    );
  }

  const isOn = selected.includes(selectedRow.id);

  return (
    <section className="min-h-0 overflow-auto bg-bg-canvas p-5">
      <div className="mx-auto max-w-3xl">
        <div className="rounded-lg border border-border bg-bg-panel p-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <div className="text-[10px] uppercase tracking-[0.18em] text-text-muted">
                {t('preview')}
              </div>
              <h3 className="mt-2 text-xl font-semibold tracking-tight text-text-primary">
                {selectedRow.title}
              </h3>
              <p className="mt-2 font-mono text-xs text-text-muted">
                {selectedRow.id}@{selectedRow.version}
              </p>
            </div>
            <PolicySwitch
              checked={isOn}
              onToggle={() => onToggle(selectedRow.id)}
              label={tPolicies('togglePolicy', {
                action: isOn ? tPolicies('deactivate') : tPolicies('activate'),
                title: selectedRow.title,
              })}
              className="mt-1"
            />
          </div>

          <div className="mt-4 grid grid-cols-3 gap-2">
            <DetailStat label={t('scope')} value={scopeLabel(selectedRow.scope)} />
            <DetailStat label={t('lang')} value={selectedRow.lang.toUpperCase()} />
            <DetailStat label={t('rules')} value={String(selectedRow.rule_count)} />
          </div>
        </div>

        <div className="mt-4 overflow-hidden rounded-lg border border-border bg-bg-panel">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <h4 className="flex items-center gap-2 text-sm font-semibold">
              <ListChecks size={15} className="text-status-info" />
              {t('rulesIncluded')}
            </h4>
            <span className="text-xs text-text-muted">
              {t('loaded', { count: rules.data?.length ?? 0 })}
            </span>
          </div>

          {rules.isLoading && (
            <div className="space-y-2 p-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-24" />
              ))}
            </div>
          )}

          <div className="divide-y divide-border">
            {rules.data?.map((rule) => (
              <div key={rule.id} className="p-4">
                <div className="mb-2 flex items-center gap-2">
                  <span className="font-mono text-xs text-text-secondary">{rule.id}</span>
                  <span className="rounded border border-border bg-bg-canvas px-2 py-0.5 text-[10px] uppercase text-text-muted">
                    {rule.rule_type}
                  </span>
                  <span
                    className={cn(
                      'ml-auto rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase',
                      rule.severity === 'fail' &&
                        'border-status-danger/30 bg-status-danger/10 text-status-danger',
                      rule.severity === 'warn' &&
                        'border-status-warning/30 bg-status-warning/10 text-status-warning',
                      rule.severity === 'info' &&
                        'border-status-info/30 bg-status-info/10 text-status-info'
                    )}
                  >
                    {rule.severity}
                  </span>
                </div>
                <p className="rounded-md border border-border bg-bg-canvas p-3 font-mono text-[11px] leading-5 text-text-secondary">
                  {rule.excerpt}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function DetailStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-bg-canvas px-3 py-2">
      <div className="text-[10px] uppercase tracking-wide text-text-muted">{label}</div>
      <div className="mt-1 truncate text-sm font-semibold text-text-primary">{value}</div>
    </div>
  );
}
