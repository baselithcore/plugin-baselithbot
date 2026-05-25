import { Globe, Pencil, Trash2, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { TenantInfo } from '../../../lib/api/admin';
import type { DomainGrant, RoleSummary } from '../../../lib/api/rbac';
import { cn } from '../../../lib/cn';
import { Button, IconButton } from '../../ui';
import { Chip, RoleBadge } from './atoms';

interface Props {
  grant: DomainGrant;
  tenant: TenantInfo | undefined;
  roles: RoleSummary[];
  busy: string | null;
  userId: string;
  isEditing: boolean;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onSaveRole: (roleId: string) => Promise<void> | void;
  onRemove: () => Promise<void> | void;
}

export function GrantRow({
  grant,
  tenant,
  roles,
  busy,
  userId,
  isEditing,
  onStartEdit,
  onCancelEdit,
  onSaveRole,
  onRemove,
}: Props) {
  const [draft, setDraft] = useState(grant.role_id ?? '');
  useEffect(() => setDraft(grant.role_id ?? ''), [grant.role_id, isEditing]);

  const removeBusy = busy === `grant:${userId}:${grant.domain_slug}`;
  const updateBusy = busy === `update:${userId}:${grant.domain_slug}`;
  const label = tenant?.label ?? grant.domain_slug;
  const unknown = !tenant;

  return (
    <li
      className={cn(
        'group rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)]',
        'px-3 py-2 transition-colors hover:border-[var(--color-border-strong)]',
        unknown && 'border-amber-500/40 bg-amber-500/5',
      )}
    >
      <div className="flex items-center gap-2.5">
        <span
          className="grid size-7 shrink-0 place-items-center rounded-md bg-[var(--color-surface)] text-ink-subtle"
          aria-hidden
        >
          <Globe size={13} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className="truncate text-[12px] font-semibold text-ink">{label}</span>
            {tenant?.is_active && <Chip tone="success">attivo</Chip>}
            {unknown && <Chip tone="warn">pack mancante</Chip>}
          </div>
          <div className="flex items-center gap-1.5 text-[10.5px] text-ink-subtle">
            <code className="rounded bg-[var(--color-surface)] px-1 py-px">{grant.domain_slug}</code>
            {tenant?.language && <span>· {tenant.language.toUpperCase()}</span>}
          </div>
        </div>
        {!isEditing && (
          <div className="flex items-center gap-1">
            {grant.role_slug ? (
              <RoleBadge slug={grant.role_slug} />
            ) : (
              <Chip>ruolo: default</Chip>
            )}
            <IconButton
              icon={Pencil}
              size="sm"
              aria-label="modifica ruolo"
              onClick={onStartEdit}
              disabled={removeBusy}
            />
            <IconButton
              icon={Trash2}
              size="sm"
              aria-label={`revoca accesso a ${grant.domain_slug}`}
              onClick={onRemove}
              disabled={removeBusy}
              className="hover:text-rose-600"
            />
          </div>
        )}
      </div>

      {isEditing && (
        <div className="mt-2 flex items-center gap-1.5 border-t border-[var(--color-border)] pt-2">
          <label className="text-[10.5px] uppercase tracking-wide text-ink-subtle">ruolo</label>
          <select
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="input-sm flex-1"
            aria-label="ruolo per il dominio"
          >
            <option value="">— eredita ruolo globale —</option>
            {roles.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name} ({r.slug})
              </option>
            ))}
          </select>
          <Button size="sm" variant="primary" loading={updateBusy} onClick={() => onSaveRole(draft)}>
            Salva
          </Button>
          <IconButton icon={X} size="sm" aria-label="annulla" onClick={onCancelEdit} />
        </div>
      )}
    </li>
  );
}
