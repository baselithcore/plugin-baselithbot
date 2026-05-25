/**
 * AdminUsersPage — gestione utenti enterprise.
 *
 * Layout: tabella full-width (email, nome, ruoli, domini, attivo) + drawer
 * dettaglio a destra per gestire ruoli e domain grants. Filtro live,
 * invito utente via dialog, copy link invito generato.
 */

import { KeyRound, UserPlus } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';

import { useAuth } from '../../contexts/AuthContext';
import { fetchTenants, type TenantInfo } from '../../lib/api/admin';
import * as rbacApi from '../../lib/api/rbac';
import type { RoleSummary, UserWithRoles } from '../../lib/api/rbac';
import { Button, Callout } from '../ui';
import { Chip, RoleBadge, Td, Th } from './users/atoms';
import { CreateUserDialog } from './users/CreateUserDialog';
import { InviteDialog } from './users/InviteDialog';
import { UserDetailPanel } from './users/UserDetailPanel';

const ROLE_ASSIGN_PERM: Record<string, string> = {
  superuser: 'rbac.assign.superuser',
  admin: 'rbac.assign.admin',
  moderator: 'rbac.assign.moderator',
  user: 'rbac.assign.user',
};

export function AdminUsersPage() {
  const { can, user: currentUser } = useAuth();
  const [users, setUsers] = useState<UserWithRoles[]>([]);
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [tenants, setTenants] = useState<TenantInfo[]>([]);
  const [filter, setFilter] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);

  const canManageRole = useCallback(
    (r: RoleSummary): boolean =>
      r.is_system ? can(ROLE_ASSIGN_PERM[r.slug] ?? 'rbac.assign.admin') : can('rbac.assign.admin'),
    [can]
  );

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [u, r, t] = await Promise.all([
        rbacApi.listUsersWithRoles(),
        rbacApi.listRoles(),
        fetchTenants().then((res) => res.tenants).catch(() => [] as TenantInfo[]),
      ]);
      setUsers(u);
      setRoles(r);
      setTenants(t);
      setSelectedId((prev) => prev ?? (u[0]?.id ?? null));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'errore caricamento');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return users;
    return users.filter(
      (u) =>
        u.email.toLowerCase().includes(q) ||
        (u.display_name ?? '').toLowerCase().includes(q) ||
        u.roles.some((r) => r.slug.includes(q))
    );
  }, [users, filter]);

  const selected = useMemo(
    () => users.find((u) => u.id === selectedId) ?? null,
    [users, selectedId]
  );

  const toggleRole = useCallback(
    async (user: UserWithRoles, role: RoleSummary) => {
      const has = user.roles.some((r) => r.id === role.id);
      const k = `role:${user.id}:${role.id}`;
      setBusy(k);
      try {
        if (has) await rbacApi.revokeRole(user.id, role.id);
        else await rbacApi.assignRole(user.id, role.id);
        await refresh();
        toast.success(has ? `Revocato ${role.slug}` : `Assegnato ${role.slug}`);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : 'operazione fallita');
      } finally {
        setBusy(null);
      }
    },
    [refresh]
  );

  const removeGrant = useCallback(
    async (user: UserWithRoles, slug: string) => {
      const k = `grant:${user.id}:${slug}`;
      setBusy(k);
      try {
        await rbacApi.revokeDomain(user.id, slug);
        await refresh();
        toast.success(`Revocato accesso a ${slug}`);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : 'revoca fallita');
      } finally {
        setBusy(null);
      }
    },
    [refresh]
  );

  const addGrant = useCallback(
    async (slug: string, roleId: string) => {
      if (!selectedId) return;
      const k = `add:${selectedId}:${slug}`;
      setBusy(k);
      try {
        await rbacApi.grantDomain(selectedId, slug, roleId || undefined);
        await refresh();
        toast.success(`Accesso a ${slug} concesso`);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : 'grant fallito');
      } finally {
        setBusy(null);
      }
    },
    [refresh, selectedId]
  );

  const updateGrant = useCallback(
    async (slug: string, roleId: string) => {
      if (!selectedId) return;
      const k = `update:${selectedId}:${slug}`;
      setBusy(k);
      try {
        await rbacApi.grantDomain(selectedId, slug, roleId || undefined);
        await refresh();
        toast.success(`Ruolo aggiornato per ${slug}`);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : 'aggiornamento fallito');
      } finally {
        setBusy(null);
      }
    },
    [refresh, selectedId]
  );

  return (
    <div className="flex h-full">
      <section className="flex flex-1 flex-col min-w-0 border-r border-[var(--color-border)]">
        <div className="flex items-center gap-3 border-b border-[var(--color-border)] px-5 py-3">
          <input
            type="search"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="cerca per email, nome, ruolo…"
            className="input-sm flex-1 max-w-md"
            aria-label="filtra utenti"
          />
          <span className="text-[11px] text-ink-subtle">
            {filtered.length} / {users.length}
          </span>
          {/* Hide-if-no-perm pattern (no disabled-button anti-pattern):
              chi non ha admin.user.manage non vede affordance. Backend
              comunque enforce su POST /users + /invite. */}
          {can('admin.user.manage') && (
            <div className="ml-auto flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setCreateOpen(true)}
              >
                <KeyRound size={13} />
                Crea utente
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => setInviteOpen(true)}
              >
                <UserPlus size={13} />
                Invita utente
              </Button>
            </div>
          )}
        </div>

        {error && (
          <Callout tone="warning" className="m-5">
            {error}
          </Callout>
        )}

        <div className="flex-1 overflow-y-auto">
          <table className="w-full border-separate border-spacing-0 text-xs">
            <thead className="sticky top-0 z-10 bg-[var(--color-canvas)] text-[10px] uppercase text-ink-subtle">
              <tr>
                <Th>Email</Th>
                <Th>Nome</Th>
                <Th>Ruoli</Th>
                <Th>Domini</Th>
                <Th>Stato</Th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-ink-subtle">
                    Caricamento…
                  </td>
                </tr>
              )}
              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-ink-subtle">
                    Nessun utente.
                  </td>
                </tr>
              )}
              {filtered.map((u) => {
                const active = u.id === selectedId;
                return (
                  <tr
                    key={u.id}
                    onClick={() => setSelectedId(u.id)}
                    className={
                      'cursor-pointer border-b border-[var(--color-border)] transition-colors ' +
                      (active
                        ? 'bg-[var(--color-brand-soft)]'
                        : 'hover:bg-[var(--color-surface-hover)]')
                    }
                  >
                    <Td className="font-medium">{u.email}</Td>
                    <Td>{u.display_name || <span className="text-ink-subtle">—</span>}</Td>
                    <Td>
                      <div className="flex flex-wrap gap-1">
                        {u.roles.length === 0 ? (
                          <span className="text-ink-subtle italic">nessuno</span>
                        ) : (
                          u.roles.map((r) => <RoleBadge key={r.id} slug={r.slug} />)
                        )}
                      </div>
                    </Td>
                    <Td>
                      <div className="flex flex-wrap gap-1">
                        {u.domain_grants.length === 0 ? (
                          <span className="text-ink-subtle italic">tutti</span>
                        ) : (
                          u.domain_grants.map((g) => {
                            const t = tenants.find((x) => x.name === g.domain_slug);
                            return (
                              <Chip key={g.domain_slug}>
                                {t?.label ?? g.domain_slug}
                                {g.role_slug ? ` · ${g.role_slug}` : ''}
                              </Chip>
                            );
                          })
                        )}
                      </div>
                    </Td>
                    <Td>
                      <Chip tone={u.is_active ? 'success' : 'danger'}>
                        {u.is_active ? 'attivo' : 'disabilitato'}
                      </Chip>
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <UserDetailPanel
        user={selected}
        roles={roles}
        tenants={tenants}
        currentUserId={currentUser?.id ?? null}
        canManageRole={canManageRole}
        busy={busy}
        onToggleRole={toggleRole}
        onRemoveGrant={removeGrant}
        onAddGrant={addGrant}
        onUpdateGrant={updateGrant}
        onLifecycleChanged={() => void refresh()}
        onLifecycleDeleted={() => {
          setSelectedId(null);
          void refresh();
        }}
      />

      <InviteDialog
        open={inviteOpen}
        roles={roles.filter(canManageRole)}
        onClose={() => setInviteOpen(false)}
        onCreated={() => {
          setInviteOpen(false);
          refresh();
        }}
      />

      <CreateUserDialog
        open={createOpen}
        roles={roles}
        assignableRoles={roles.filter(canManageRole)}
        onClose={() => setCreateOpen(false)}
        onCreated={() => {
          refresh();
        }}
      />
    </div>
  );
}
