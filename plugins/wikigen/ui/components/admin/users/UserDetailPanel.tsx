import type { TenantInfo } from '../../../lib/api/admin';
import type { RoleSummary, UserWithRoles } from '../../../lib/api/rbac';
import { DomainGrantsSection } from './DomainGrantsSection';
import { RolesSection } from './RolesSection';
import { UserDangerZone } from './UserDangerZone';
import { UserHeader } from './UserHeader';

interface Props {
  user: UserWithRoles | null;
  roles: RoleSummary[];
  tenants: TenantInfo[];
  currentUserId: string | null;
  canManageRole: (r: RoleSummary) => boolean;
  busy: string | null;
  onToggleRole: (u: UserWithRoles, r: RoleSummary) => void;
  onAddGrant: (slug: string, roleId: string) => Promise<void> | void;
  onUpdateGrant: (slug: string, roleId: string) => Promise<void> | void;
  onRemoveGrant: (u: UserWithRoles, slug: string) => void;
  onLifecycleChanged: () => void | Promise<void>;
  onLifecycleDeleted: () => void;
}

export function UserDetailPanel({
  user,
  roles,
  tenants,
  currentUserId,
  canManageRole,
  busy,
  onToggleRole,
  onAddGrant,
  onUpdateGrant,
  onRemoveGrant,
  onLifecycleChanged,
  onLifecycleDeleted,
}: Props) {
  if (!user) {
    return (
      <aside className="hidden w-[22rem] shrink-0 flex-col p-6 text-xs text-ink-subtle lg:flex">
        Seleziona un utente per gestirne ruoli e accessi.
      </aside>
    );
  }

  return (
    <aside className="hidden w-[22rem] shrink-0 flex-col overflow-y-auto border-l border-[var(--color-border)] bg-[var(--color-canvas-raised)] p-5 lg:flex">
      <UserHeader user={user} />
      <RolesSection
        user={user}
        roles={roles}
        canManageRole={canManageRole}
        busy={busy}
        onToggleRole={onToggleRole}
      />
      <DomainGrantsSection
        user={user}
        tenants={tenants}
        roles={roles}
        canManageRole={canManageRole}
        busy={busy}
        onAddGrant={({ slug, roleId }) => onAddGrant(slug, roleId)}
        onUpdateGrant={({ slug, roleId }) => onUpdateGrant(slug, roleId)}
        onRemoveGrant={(slug) => onRemoveGrant(user, slug)}
      />
      <UserDangerZone
        user={user}
        currentUserId={currentUserId}
        onChanged={onLifecycleChanged}
        onDeleted={onLifecycleDeleted}
      />
    </aside>
  );
}
