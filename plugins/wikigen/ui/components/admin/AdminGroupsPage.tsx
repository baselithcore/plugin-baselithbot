/**
 * AdminGroupsPage — gestione gruppi (mig 015).
 *
 * Pattern allineato a AdminUsersPage: lista a sinistra, drawer dettaglio
 * a destra per membership + ruoli. Toolbar con filtro + bottone "Nuovo
 * gruppo".
 *
 * Gating UI: tutto richiede `admin.group.manage`. Il toggle di ruoli
 * dentro un gruppo richiede inoltre `rbac.assign.<slug>` corrispondente
 * (server lo enforce, qui disabilitiamo i checkbox per UX coerente).
 */

import { Plus, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';

import { useAuth } from '../../contexts/AuthContext';
import * as groupsApi from '../../lib/api/groups';
import type { GroupSummary } from '../../lib/api/groups';
import * as rbacApi from '../../lib/api/rbac';
import type { RoleSummary, UserWithRoles } from '../../lib/api/rbac';
import { Button, Callout } from '../ui';
import { CreateGroupDialog } from './groups/CreateGroupDialog';
import { GroupDetailPanel } from './groups/GroupDetailPanel';

const ROLE_ASSIGN_PERM: Record<string, string> = {
  superuser: 'rbac.assign.superuser',
  admin: 'rbac.assign.admin',
  moderator: 'rbac.assign.moderator',
  user: 'rbac.assign.user',
};

export function AdminGroupsPage() {
  const { can } = useAuth();
  const [groups, setGroups] = useState<GroupSummary[]>([]);
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [users, setUsers] = useState<UserWithRoles[]>([]);
  const [filter, setFilter] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [g, r, u] = await Promise.all([
        groupsApi.listGroups(),
        rbacApi.listRoles(),
        rbacApi.listUsersWithRoles(),
      ]);
      setGroups(g);
      setRoles(r);
      setUsers(u);
      setSelectedId((prev) => prev ?? g[0]?.id ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'errore caricamento');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return groups;
    return groups.filter(
      (g) =>
        g.name.toLowerCase().includes(q) ||
        g.slug.toLowerCase().includes(q) ||
        g.description.toLowerCase().includes(q)
    );
  }, [groups, filter]);

  const canAssignRole = useCallback(
    (slug: string, isSystem: boolean): boolean =>
      isSystem ? can(ROLE_ASSIGN_PERM[slug] ?? 'rbac.assign.admin') : can('rbac.assign.admin'),
    [can]
  );

  const deleteGroup = useCallback(
    async (g: GroupSummary) => {
      if (g.is_system) {
        toast.error('Gruppo system non eliminabile');
        return;
      }
      if (!window.confirm(`Eliminare il gruppo "${g.name}"?`)) return;
      try {
        await groupsApi.deleteGroup(g.id);
        toast.success(`Eliminato "${g.name}"`);
        if (selectedId === g.id) setSelectedId(null);
        await refresh();
      } catch (e) {
        toast.error(e instanceof Error ? e.message : 'eliminazione fallita');
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
            placeholder="cerca per nome, slug, descrizione…"
            className="input-sm flex-1 max-w-md"
            aria-label="filtra gruppi"
          />
          <span className="text-[11px] text-ink-subtle">
            {filtered.length} / {groups.length}
          </span>
          {can('admin.group.manage') && (
            <div className="ml-auto">
              <Button
                variant="primary"
                size="sm"
                onClick={() => setCreateOpen(true)}
              >
                <Plus size={13} />
                Nuovo gruppo
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
                <th className="px-5 py-2 text-left">Nome</th>
                <th className="px-5 py-2 text-left">Slug</th>
                <th className="px-5 py-2 text-left">Membri</th>
                <th className="px-5 py-2 text-left">Ruoli</th>
                <th className="px-5 py-2 text-left">Tipo</th>
                <th className="px-5 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-ink-subtle">
                    Caricamento…
                  </td>
                </tr>
              )}
              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-ink-subtle">
                    Nessun gruppo. Crea il primo con "Nuovo gruppo".
                  </td>
                </tr>
              )}
              {filtered.map((g) => {
                const isSel = g.id === selectedId;
                return (
                  <tr
                    key={g.id}
                    onClick={() => setSelectedId(g.id)}
                    className={
                      'cursor-pointer border-b border-[var(--color-border)] ' +
                      (isSel
                        ? 'bg-[var(--color-brand-soft)]'
                        : 'hover:bg-[var(--color-surface-hover)]')
                    }
                  >
                    <td className="px-5 py-2 font-medium">{g.name}</td>
                    <td className="px-5 py-2 font-mono text-ink-subtle">{g.slug}</td>
                    <td className="px-5 py-2">{g.member_count}</td>
                    <td className="px-5 py-2">{g.role_count}</td>
                    <td className="px-5 py-2 text-[10px] text-ink-subtle uppercase">
                      {g.is_system ? 'system' : 'custom'}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {!g.is_system && (
                        <button
                          type="button"
                          className="btn-ghost text-danger"
                          onClick={(e) => {
                            e.stopPropagation();
                            void deleteGroup(g);
                          }}
                          aria-label={`Elimina ${g.name}`}
                        >
                          <Trash2 size={12} />
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {selectedId && (
        <GroupDetailPanel
          key={selectedId}
          groupId={selectedId}
          allRoles={roles}
          allUsers={users}
          canAssignRole={canAssignRole}
          onChanged={() => void refresh()}
        />
      )}

      <CreateGroupDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={() => void refresh()}
      />
    </div>
  );
}
