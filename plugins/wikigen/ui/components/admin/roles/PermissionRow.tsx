import { Check, Lock, Minus } from 'lucide-react';
import type { PermissionEntry, RoleSummary } from '../../../lib/api/rbac';
import { cn } from '../../../lib/cn';
import { describePermission } from './permission_catalog';

interface Props {
  perm: PermissionEntry;
  roles: RoleSummary[];
  draft: Record<string, Set<string>>;
  original: Record<string, Set<string>>;
  canEdit: boolean;
  onTogglePerm: (roleId: string, slug: string) => void;
  isLocked: (r: RoleSummary) => boolean;
}

export function PermissionRow({
  perm,
  roles,
  draft,
  original,
  canEdit,
  onTogglePerm,
  isLocked,
}: Props) {
  const description = describePermission(perm.slug, perm.description);
  return (
    <tr className="group hover:bg-[var(--color-surface-hover)]/40">
      <th
        scope="row"
        className="sticky left-0 z-10 border-b border-r border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-3 py-1.5 text-left align-middle group-hover:bg-[var(--color-surface-hover)]/40"
        style={{ minWidth: 280 }}
      >
        <div className="flex flex-col gap-0.5">
          <code className="text-[11px] font-semibold text-ink">{perm.slug}</code>
          <span className="text-[10.5px] leading-snug text-ink-subtle">{description}</span>
        </div>
      </th>
      {roles.map((r) => {
        const checked = draft[r.id]?.has(perm.slug) ?? false;
        const was = original[r.id]?.has(perm.slug) ?? false;
        const changed = checked !== was;
        const locked = isLocked(r) || !canEdit;
        return (
          <td
            key={r.id}
            className={cn(
              'border-b border-[var(--color-border)] p-0 align-middle',
              changed && 'bg-[var(--color-brand-soft)]',
            )}
          >
            <button
              type="button"
              disabled={locked}
              onClick={() => onTogglePerm(r.id, perm.slug)}
              aria-pressed={checked}
              aria-label={`${checked ? 'rimuovi' : 'assegna'} ${perm.slug} a ${r.slug}`}
              className={cn(
                'focus-ring grid h-9 w-full place-items-center transition-colors',
                'disabled:cursor-not-allowed',
                !locked && 'hover:bg-[var(--color-surface-hover)]',
              )}
            >
              <ToggleCell checked={checked} changed={changed} locked={locked && isLocked(r)} />
            </button>
          </td>
        );
      })}
    </tr>
  );
}

function ToggleCell({
  checked,
  changed,
  locked,
}: {
  checked: boolean;
  changed: boolean;
  locked: boolean;
}) {
  if (locked) {
    return (
      <span
        className={cn(
          'grid size-5 place-items-center rounded',
          checked ? 'bg-[var(--color-brand)]/30 text-[var(--color-brand)]' : 'text-ink-subtle',
        )}
        aria-hidden
      >
        {checked ? <Check size={11} strokeWidth={3} /> : <Lock size={10} />}
      </span>
    );
  }
  if (checked) {
    return (
      <span
        className={cn(
          'grid size-5 place-items-center rounded shadow-sm',
          changed
            ? 'bg-emerald-500 text-white ring-2 ring-emerald-500/30'
            : 'bg-[var(--color-brand)] text-white',
        )}
        aria-hidden
      >
        <Check size={12} strokeWidth={3} />
      </span>
    );
  }
  return (
    <span
      className={cn(
        'grid size-5 place-items-center rounded border border-dashed',
        changed
          ? 'border-rose-500/60 bg-rose-500/10 text-rose-600 dark:text-rose-400'
          : 'border-[var(--color-border-strong)] text-transparent group-hover:text-ink-subtle',
      )}
      aria-hidden
    >
      {changed ? <Minus size={11} /> : <Check size={11} />}
    </span>
  );
}
