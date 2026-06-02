import { ChevronRight } from 'lucide-react';
import { Fragment } from 'react';
import type { PermissionEntry, RoleSummary } from '../../../lib/api/rbac';
import { cn } from '../../../lib/cn';
import type { GroupMeta } from './permission_catalog';
import { PermissionRow } from './PermissionRow';

interface Props {
  group: GroupMeta;
  perms: PermissionEntry[];
  roles: RoleSummary[];
  draft: Record<string, Set<string>>;
  original: Record<string, Set<string>>;
  collapsed: boolean;
  canEdit: boolean;
  onToggleCollapse: () => void;
  onTogglePerm: (roleId: string, slug: string) => void;
  onBulkSetGroup: (roleId: string, slugs: string[], value: boolean) => void;
  isLocked: (r: RoleSummary) => boolean;
}

export function GroupSection({
  group,
  perms,
  roles,
  draft,
  original,
  collapsed,
  canEdit,
  onToggleCollapse,
  onTogglePerm,
  onBulkSetGroup,
  isLocked,
}: Props) {
  const Icon = group.icon;
  const slugs = perms.map((p) => p.slug);
  const groupTotal = perms.length;

  const perRoleCount = roles.map((r) => {
    const set = draft[r.id] ?? new Set();
    let n = 0;
    for (const s of slugs) if (set.has(s)) n++;
    return { id: r.id, n, locked: isLocked(r) };
  });

  return (
    <Fragment>
      <tr className="bg-[var(--color-surface)]">
        <th
          scope="row"
          className="sticky left-0 z-10 border-b border-r border-t border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-left"
          style={{ minWidth: 280 }}
        >
          <button
            type="button"
            onClick={onToggleCollapse}
            aria-expanded={!collapsed}
            className="focus-ring inline-flex w-full items-center gap-2 rounded px-1 py-0.5 text-left hover:bg-[var(--color-surface-hover)]"
          >
            <ChevronRight
              size={12}
              className={cn(
                'shrink-0 transition-transform text-ink-subtle',
                !collapsed && 'rotate-90'
              )}
              aria-hidden
            />
            <Icon size={13} className="shrink-0 text-ink-subtle" aria-hidden />
            <span className="text-[11px] font-semibold uppercase tracking-wide text-ink">
              {group.label}
            </span>
            <span className="text-[10px] text-ink-subtle">{groupTotal}</span>
          </button>
          {group.tabs && group.tabs.length > 0 && (
            <div
              className="mt-0.5 pl-6 text-[10px] leading-tight text-ink-subtle"
              title={`Superfici UI controllate da ${group.label}`}
            >
              <span className="font-medium">Mostra/nasconde:</span> {group.tabs.join(' · ')}
            </div>
          )}
        </th>
        {roles.map((r, idx) => {
          const info = perRoleCount[idx];
          const all = info.n === groupTotal;
          const none = info.n === 0;
          const next = all ? false : true;
          return (
            <td
              key={r.id}
              className="border-b border-t border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 align-middle"
            >
              <div className="flex items-center justify-between gap-1.5">
                <span className="text-[10px] font-mono text-ink-subtle">
                  {info.n}/{groupTotal}
                </span>
                {!info.locked && canEdit && (
                  <button
                    type="button"
                    onClick={() => onBulkSetGroup(r.id, slugs, next)}
                    className={cn(
                      'focus-ring rounded px-1.5 py-0.5 text-[10px] font-medium transition-colors',
                      none
                        ? 'text-[var(--color-brand)] hover:bg-[var(--color-brand-soft)]'
                        : all
                          ? 'text-rose-600 hover:bg-rose-500/10 dark:text-rose-400'
                          : 'text-[var(--color-brand)] hover:bg-[var(--color-brand-soft)]'
                    )}
                    title={
                      all
                        ? `Rimuovi tutti i permessi ${group.label.toLowerCase()} da ${r.slug}`
                        : `Assegna tutti i permessi ${group.label.toLowerCase()} a ${r.slug}`
                    }
                  >
                    {all ? 'rimuovi tutti' : 'tutti'}
                  </button>
                )}
              </div>
            </td>
          );
        })}
      </tr>
      {!collapsed &&
        perms.map((p) => (
          <PermissionRow
            key={p.slug}
            perm={p}
            roles={roles}
            draft={draft}
            original={original}
            canEdit={canEdit}
            onTogglePerm={onTogglePerm}
            isLocked={isLocked}
          />
        ))}
    </Fragment>
  );
}
