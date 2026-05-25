import { Lock, RotateCcw, Save } from 'lucide-react';
import type { RoleSummary } from '../../../lib/api/rbac';
import { cn } from '../../../lib/cn';
import { IconButton } from '../../ui';
import { Chip, RoleBadge } from '../users/atoms';
import type { RoleDiff } from './utils';

interface Props {
  role: RoleSummary;
  totalGranted: number;
  totalAvailable: number;
  diff: RoleDiff;
  locked: boolean;
  canEdit: boolean;
  saving: boolean;
  onSave: () => void;
  onReset: () => void;
}

export function RoleHeader({
  role,
  totalGranted,
  totalAvailable,
  diff,
  locked,
  canEdit,
  saving,
  onSave,
  onReset,
}: Props) {
  const dirty = diff.total > 0;
  return (
    <th
      scope="col"
      className={cn(
        'sticky top-[44px] z-20 border-b border-[var(--color-border)] bg-[var(--color-canvas)] p-0 text-left align-top',
      )}
      style={{ minWidth: 180 }}
    >
      <div
        className={cn(
          'flex h-full flex-col gap-1.5 border-r border-[var(--color-border)] px-3 py-3',
          dirty && 'bg-[var(--color-brand-soft)]',
        )}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <RoleBadge slug={role.slug} size="md" />
              {locked && (
                <span
                  className="inline-flex items-center gap-1 rounded px-1 py-0.5 text-[10px] text-ink-subtle"
                  title="Ruolo protetto — guard backend, sola lettura"
                >
                  <Lock size={10} aria-hidden />
                  protetto
                </span>
              )}
            </div>
            <p className="mt-0.5 truncate text-[12px] font-semibold text-ink">{role.name}</p>
            <p className="text-[10px] text-ink-subtle">
              {totalGranted} / {totalAvailable} permessi
            </p>
          </div>
        </div>

        {dirty && (
          <div className="flex flex-wrap items-center gap-1">
            {diff.added.length > 0 && (
              <Chip tone="success" className="font-mono">+{diff.added.length}</Chip>
            )}
            {diff.removed.length > 0 && (
              <Chip tone="danger" className="font-mono">−{diff.removed.length}</Chip>
            )}
          </div>
        )}

        {!locked && (
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={onSave}
              disabled={!canEdit || !dirty || saving}
              className={cn(
                'focus-ring inline-flex flex-1 items-center justify-center gap-1 rounded-md',
                'min-h-7 px-2 text-[11px] font-semibold transition-colors',
                'disabled:cursor-not-allowed disabled:opacity-40',
                dirty
                  ? 'bg-[var(--color-brand)] text-white hover:bg-[var(--color-brand-strong)]'
                  : 'border border-[var(--color-border)] bg-[var(--color-canvas-raised)] text-ink-subtle',
              )}
            >
              <Save size={11} aria-hidden />
              {saving ? 'Salvo…' : dirty ? 'Salva' : 'Salvato'}
            </button>
            {dirty && (
              <IconButton
                icon={RotateCcw}
                size="sm"
                aria-label="annulla modifiche"
                onClick={onReset}
                disabled={saving}
              />
            )}
          </div>
        )}
      </div>
    </th>
  );
}
