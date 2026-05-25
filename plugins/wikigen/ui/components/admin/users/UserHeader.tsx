import { Copy } from 'lucide-react';
import { toast } from 'sonner';
import type { UserWithRoles } from '../../../lib/api/rbac';
import { IconButton } from '../../ui';
import { Avatar, Chip, RoleBadge } from './atoms';

export function UserHeader({ user }: { user: UserWithRoles }) {
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(user.email);
      toast.success('Email copiata');
    } catch {
      toast.error('Copia fallita');
    }
  };

  return (
    <header className="mb-5 flex items-start gap-3">
      <Avatar email={user.email} displayName={user.display_name} size={44} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <h3 className="truncate text-[13px] font-semibold text-ink">
            {user.display_name || user.email.split('@')[0]}
          </h3>
          <Chip tone={user.is_active ? 'success' : 'danger'}>
            {user.is_active ? 'attivo' : 'disabilitato'}
          </Chip>
        </div>
        <div className="mt-0.5 flex items-center gap-1 text-[11px] text-ink-subtle">
          <span className="truncate">{user.email}</span>
          <IconButton
            icon={Copy}
            size="sm"
            aria-label="copia email"
            onClick={copy}
            className="-my-1"
          />
        </div>
        <p className="mt-1 text-[10px] text-ink-subtle">
          tenant <code className="rounded bg-[var(--color-surface)] px-1">{user.tenant_id.slice(0, 8)}…</code>
        </p>
        {user.roles.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {user.roles.map((r) => (
              <RoleBadge key={r.id} slug={r.slug} />
            ))}
          </div>
        )}
      </div>
    </header>
  );
}
