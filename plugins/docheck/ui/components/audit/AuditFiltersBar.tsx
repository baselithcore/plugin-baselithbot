'use client';

import { Search, X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import type { AuditFilters, AuditUserOption } from '@/lib/api/audit';
import { cn } from '@/lib/cn';

export interface FiltersState extends AuditFilters {
  limit: number;
  offset: number;
}

interface Props {
  actions: string[];
  users: AuditUserOption[];
  filters: FiltersState;
  resourceInput: string;
  setResourceInput: (s: string) => void;
  onSearchSubmit: (e: React.FormEvent) => void;
  setFilter: (patch: Partial<FiltersState>) => void;
  clear: () => void;
  hasActive: boolean;
}

export function AuditFiltersBar({
  actions,
  users,
  filters,
  resourceInput,
  setResourceInput,
  onSearchSubmit,
  setFilter,
  clear,
  hasActive,
}: Props) {
  const t = useTranslations('audit.filters');
  return (
    <Card className="mb-4 p-3">
      <div className="flex flex-wrap items-end gap-3">
        <Field label={t('user')}>
          <select
            className={selectCls}
            value={filters.user_id ?? ''}
            onChange={(e) => setFilter({ user_id: e.target.value || undefined })}
          >
            <option value="">{t('all')}</option>
            {users.map((u) => (
              <option key={u.user_id} value={u.user_id}>
                {u.email || u.display_name || u.user_id}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t('action')}>
          <select
            className={selectCls}
            value={filters.action ?? ''}
            onChange={(e) => setFilter({ action: e.target.value || undefined })}
          >
            <option value="">{t('all')}</option>
            {actions.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t('from')}>
          <input
            type="date"
            className={selectCls}
            value={filters.date_from ?? ''}
            onChange={(e) => setFilter({ date_from: e.target.value || undefined })}
          />
        </Field>
        <Field label={t('to')}>
          <input
            type="date"
            className={selectCls}
            value={filters.date_to ?? ''}
            onChange={(e) => setFilter({ date_to: e.target.value || undefined })}
          />
        </Field>
        <form onSubmit={onSearchSubmit} className="flex-1 min-w-[200px]">
          <Field label={t('resourceSearch')}>
            <div className="relative">
              <Search
                size={13}
                className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted"
              />
              <input
                type="text"
                placeholder={t('resourcePlaceholder')}
                className={cn(selectCls, 'pl-8 w-full')}
                value={resourceInput}
                onChange={(e) => setResourceInput(e.target.value)}
              />
            </div>
          </Field>
        </form>
        {hasActive && (
          <Button size="sm" variant="ghost" onClick={clear}>
            <X size={13} /> {t('clear')}
          </Button>
        )}
      </div>
    </Card>
  );
}

const selectCls =
  'h-8 rounded-md border border-border bg-bg-canvas px-2.5 text-xs text-text-primary focus:outline-none focus:border-status-info';

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] font-semibold uppercase tracking-wide text-text-muted">
        {label}
      </span>
      {children}
    </label>
  );
}
