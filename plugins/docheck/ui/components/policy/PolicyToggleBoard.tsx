'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import {
  CheckCircle2,
  FileText,
  ListChecks,
  Search,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
} from 'lucide-react';
import { listPolicies, type PolicyRow } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/cn';

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

interface Props {
  compact?: boolean;
  onConfigure?: () => void;
}

export function PolicyToggleBoard({ compact, onConfigure }: Props) {
  const t = useTranslations('policies');
  const scopeLabel = useScopeLabel();
  const [query, setQuery] = useState('');
  const selected = useAppStore((s) => s.selectedPolicies);
  const setSelected = useAppStore((s) => s.setSelectedPolicies);
  const policies = useQuery({
    queryKey: ['policies'],
    queryFn: listPolicies,
    staleTime: 60_000,
  });

  // Auto-seed selection with all active policies on first load to avoid
  // the "Policies 0 → score=100 vacuous" trap. User can still opt-out manually.
  const seededRef = useRef(false);
  useEffect(() => {
    if (seededRef.current) return;
    if (!policies.data || selected.length > 0) return;
    const activeIds = policies.data.filter((p) => p.active).map((p) => p.id);
    if (activeIds.length > 0) {
      seededRef.current = true;
      setSelected(activeIds);
    }
  }, [policies.data, selected.length, setSelected]);

  const rows = useMemo(() => {
    const source = policies.data ?? [];
    const selectedRows = selected
      .filter((id) => !source.some((p) => p.id === id))
      .map<PolicyRow>((id) => ({
        id,
        version: 'active',
        title: humanizePolicyId(id),
        scope: 'custom',
        lang: 'it',
        active: true,
        rule_count: 0,
      }));
    return [...source, ...selectedRows];
  }, [policies.data, selected]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (p) =>
        p.title.toLowerCase().includes(q) ||
        p.id.toLowerCase().includes(q) ||
        scopeLabel(p.scope).toLowerCase().includes(q)
    );
  }, [query, rows, scopeLabel]);

  const selectedRows = rows.filter((p) => selected.includes(p.id));
  const selectedRules = selectedRows.reduce((sum, p) => sum + p.rule_count, 0);
  const allVisibleSelected = filtered.length > 0 && filtered.every((p) => selected.includes(p.id));

  function toggle(id: string) {
    setSelected(selected.includes(id) ? selected.filter((p) => p !== id) : [...selected, id]);
  }

  function selectVisible() {
    const ids = new Set(selected);
    filtered.forEach((p) => ids.add(p.id));
    setSelected(Array.from(ids));
  }

  function clearVisible() {
    const visible = new Set(filtered.map((p) => p.id));
    setSelected(selected.filter((id) => !visible.has(id)));
  }

  return (
    <section
      className={cn(
        'rounded-xl border border-border/60 bg-bg-canvas/70 shadow-inner-soft',
        compact ? 'p-4' : 'p-5'
      )}
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="inline-flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-text-muted">
            <SlidersHorizontal size={12} />
            {t('boardEyebrow')}
          </div>
          <h3 className="mt-1 text-sm font-semibold tracking-tight text-text-primary">
            {t('boardTitle')}
          </h3>
        </div>

        <div className="grid grid-cols-3 gap-2 sm:min-w-[300px]">
          <PolicyStat
            label={t('stats.policies')}
            value={String(selected.length)}
            tone={selected.length ? 'success' : 'muted'}
          />
          <PolicyStat label={t('stats.rules')} value={String(selectedRules)} tone="info" />
          <PolicyStat
            label={t('stats.scope')}
            value={String(new Set(selectedRows.map((p) => p.scope)).size)}
            tone="warning"
          />
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center">
        <label className="flex h-9 min-w-0 flex-1 items-center gap-2 rounded-md border border-border bg-bg-panel px-3 text-xs text-text-muted transition-colors focus-within:border-status-info/60 focus-within:ring-2 focus-within:ring-status-info/20">
          <Search size={14} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('search')}
            className="min-w-0 flex-1 bg-transparent text-text-primary outline-none placeholder:text-text-muted"
          />
        </label>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={allVisibleSelected ? clearVisible : selectVisible}
          >
            <CheckCircle2 size={13} />
            {allVisibleSelected ? t('turnOffVisible') : t('turnOnVisible')}
          </Button>
          {onConfigure && (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={onConfigure}
              aria-label={t('openManager')}
            >
              <Settings2 size={13} />
            </Button>
          )}
        </div>
      </div>

      {policies.isLoading && !policies.data && (
        <div className="mt-4 grid gap-2 md:grid-cols-2">
          {Array.from({ length: compact ? 2 : 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      )}

      <div className={cn('mt-4 grid gap-2', compact ? 'lg:grid-cols-2' : 'md:grid-cols-2')}>
        {filtered.map((policy) => (
          <PolicyToggleRow
            key={`${policy.id}@${policy.version}`}
            policy={policy}
            checked={selected.includes(policy.id)}
            onToggle={() => toggle(policy.id)}
            scopeLabel={scopeLabel(policy.scope)}
          />
        ))}
      </div>

      {!policies.isLoading && filtered.length === 0 && (
        <div className="mt-4 rounded-lg border border-dashed border-border bg-bg-panel/50 px-4 py-6 text-center text-xs text-text-muted">
          {t('boardNoMatch')}
        </div>
      )}
    </section>
  );
}

export function PolicySwitch({
  checked,
  onToggle,
  label,
  className,
}: {
  checked: boolean;
  onToggle: () => void;
  label: string;
  className?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={(event) => {
        event.stopPropagation();
        onToggle();
      }}
      className={cn(
        'relative inline-flex h-7 w-12 shrink-0 items-center rounded-full border p-0.5 transition-all duration-200 ease-smooth ring-focus',
        checked
          ? 'border-status-success/60 bg-status-success'
          : 'border-border-strong bg-bg-panel-elev hover:border-text-muted',
        className
      )}
    >
      <span
        className={cn(
          'h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-200 ease-smooth',
          checked ? 'translate-x-5' : 'translate-x-0 bg-text-secondary'
        )}
      />
    </button>
  );
}

function PolicyToggleRow({
  policy,
  checked,
  onToggle,
  scopeLabel,
}: {
  policy: PolicyRow;
  checked: boolean;
  onToggle: () => void;
  scopeLabel: string;
}) {
  const t = useTranslations('policies');
  return (
    <div
      className={cn(
        'group flex min-h-[78px] min-w-0 items-center gap-3 rounded-lg border px-3 py-3 transition-all duration-200',
        checked
          ? 'border-status-success/45 bg-status-success/10 shadow-[inset_3px_0_0_rgba(16,185,129,0.85)]'
          : 'border-border bg-bg-panel/75 hover:border-border-strong hover:bg-bg-panel-elev'
      )}
    >
      <span
        className={cn(
          'flex h-10 w-10 shrink-0 items-center justify-center rounded-md border',
          checked
            ? 'border-status-success/35 bg-status-success/10 text-status-success'
            : 'border-border bg-bg-canvas text-text-muted'
        )}
      >
        {policy.active ? <ShieldCheck size={17} /> : <FileText size={17} />}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-2">
          <p
            className="min-w-0 truncate text-sm font-semibold text-text-primary"
            title={policy.title}
          >
            {policy.title}
          </p>
          <span className="shrink-0 rounded border border-border bg-bg-canvas px-1.5 py-0.5 text-[10px] uppercase text-text-muted">
            {scopeLabel}
          </span>
        </div>
        <div className="mt-1 flex min-w-0 items-center gap-x-2 gap-y-1 text-[11px] text-text-muted">
          <span
            className="block min-w-0 flex-1 truncate font-mono"
            title={`${policy.id}@${policy.version}`}
          >
            {policy.id}@{policy.version}
          </span>
          <span className="inline-flex shrink-0 items-center gap-1">
            <ListChecks size={11} />
            {policy.rule_count}
          </span>
          <span className="shrink-0">{policy.lang.toUpperCase()}</span>
        </div>
      </div>
      <PolicySwitch
        checked={checked}
        onToggle={onToggle}
        label={t('togglePolicy', {
          action: checked ? t('deactivate') : t('activate'),
          title: policy.title,
        })}
      />
    </div>
  );
}

function PolicyStat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: 'success' | 'warning' | 'info' | 'muted';
}) {
  const toneClass = {
    success: 'text-status-success',
    warning: 'text-status-warning',
    info: 'text-status-info',
    muted: 'text-text-muted',
  }[tone];
  return (
    <div className="rounded-md border border-border bg-bg-panel px-3 py-2 text-left">
      <div className="text-[10px] uppercase tracking-wide text-text-muted">{label}</div>
      <div className={cn('mt-0.5 text-base font-semibold tabular-nums', toneClass)}>{value}</div>
    </div>
  );
}

function humanizePolicyId(id: string) {
  return id.replace(/[_-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
