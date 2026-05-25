import { Plus, Search, X } from 'lucide-react';
import { useEffect, useRef } from 'react';
import type { TenantInfo } from '../../../lib/api/admin';
import type { RoleSummary } from '../../../lib/api/rbac';
import { cn } from '../../../lib/cn';
import { Button, IconButton } from '../../ui';
import { Chip } from './atoms';

interface PickerProps {
  query: string;
  setQuery: (q: string) => void;
  available: TenantInfo[];
  selected: string;
  roleId: string;
  roles: RoleSummary[];
  busy: boolean;
  onSelect: (slug: string) => void;
  onRoleChange: (roleId: string) => void;
  onCancel: () => void;
  onConfirm: () => Promise<void> | void;
}

export function DomainPicker({
  query,
  setQuery,
  available,
  selected,
  roleId,
  roles,
  busy,
  onSelect,
  onRoleChange,
  onCancel,
  onConfirm,
}: PickerProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  return (
    <div className="mt-1 rounded-xl border border-[var(--color-border)] bg-[var(--color-canvas-raised)] shadow-sm">
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-3 py-2">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-ink-subtle">
          {selected ? 'Configura accesso' : 'Seleziona dominio'}
        </span>
        <IconButton icon={X} size="sm" aria-label="chiudi" onClick={onCancel} />
      </div>

      {!selected && (
        <>
          <div className="relative border-b border-[var(--color-border)] px-3 py-2">
            <Search
              size={12}
              className="pointer-events-none absolute left-5 top-1/2 -translate-y-1/2 text-ink-subtle"
              aria-hidden
            />
            <input
              ref={inputRef}
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="cerca dominio per nome o slug…"
              className="input-sm pl-7"
              aria-label="cerca dominio"
            />
          </div>
          <ul className="max-h-64 overflow-y-auto p-1.5" role="listbox">
            {available.length === 0 ? (
              <li className="px-3 py-6 text-center text-[11px] text-ink-subtle">
                {query ? 'Nessun dominio corrisponde' : 'Tutti i domini sono già concessi'}
              </li>
            ) : (
              available.map((t) => <TenantRow key={t.name} tenant={t} onSelect={onSelect} />)
            )}
          </ul>
        </>
      )}

      {selected && (
        <div className="p-3">
          <p className="mb-2 text-[11px] text-ink-subtle">
            Dominio selezionato:{' '}
            <code className="rounded bg-[var(--color-surface)] px-1 py-px font-mono">
              {selected}
            </code>
          </p>
          <fieldset>
            <legend className="mb-1.5 text-[10.5px] font-semibold uppercase tracking-wide text-ink-subtle">
              ruolo applicato a questo dominio
            </legend>
            <div className="grid grid-cols-2 gap-1.5">
              <RoleOption
                checked={roleId === ''}
                onChange={() => onRoleChange('')}
                title="Eredita"
                desc="Usa il ruolo globale dell’utente"
              />
              {roles.map((r) => (
                <RoleOption
                  key={r.id}
                  checked={roleId === r.id}
                  onChange={() => onRoleChange(r.id)}
                  title={r.name}
                  desc={r.slug}
                />
              ))}
            </div>
          </fieldset>
          <div className="mt-3 flex items-center justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => onSelect('')}>
              Indietro
            </Button>
            <Button size="sm" variant="primary" loading={busy} onClick={onConfirm}>
              Conferma accesso
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function TenantRow({ tenant, onSelect }: { tenant: TenantInfo; onSelect: (slug: string) => void }) {
  return (
    <li>
      <button
        type="button"
        role="option"
        aria-selected="false"
        onClick={() => onSelect(tenant.name)}
        className={cn(
          'focus-ring w-full rounded-md px-2.5 py-1.5 text-left transition-colors',
          'hover:bg-[var(--color-surface)]'
        )}
      >
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="truncate text-[12px] font-medium text-ink">{tenant.label}</span>
              {tenant.is_active && <Chip tone="success">attivo</Chip>}
              {tenant.is_seed && <Chip>seed</Chip>}
              {!tenant.valid && <Chip tone="warn">invalido</Chip>}
            </div>
            <div className="text-[10.5px] text-ink-subtle">
              <code className="rounded bg-[var(--color-surface)] px-1 py-px">{tenant.name}</code>
              {tenant.description && (
                <span className="ml-1.5 line-clamp-1">{tenant.description}</span>
              )}
            </div>
          </div>
          <Plus size={12} className="shrink-0 text-ink-subtle" aria-hidden />
        </div>
      </button>
    </li>
  );
}

function RoleOption({
  checked,
  onChange,
  title,
  desc,
}: {
  checked: boolean;
  onChange: () => void;
  title: string;
  desc: string;
}) {
  return (
    <label
      className={cn(
        'focus-within:focus-ring flex cursor-pointer items-start gap-2 rounded-lg border px-2.5 py-2 text-left transition-colors',
        checked
          ? 'border-[var(--color-brand)] bg-[var(--color-brand-soft)]'
          : 'border-[var(--color-border)] bg-[var(--color-canvas-raised)] hover:border-[var(--color-border-strong)]'
      )}
    >
      <input
        type="radio"
        checked={checked}
        onChange={onChange}
        className="mt-0.5 accent-[var(--color-brand)]"
      />
      <span className="min-w-0">
        <span className="block text-[11.5px] font-semibold text-ink">{title}</span>
        <span className="block text-[10px] text-ink-subtle">{desc}</span>
      </span>
    </label>
  );
}
