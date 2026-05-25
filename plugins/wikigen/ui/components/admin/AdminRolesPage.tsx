/**
 * AdminRolesPage — matrice ruoli × permessi.
 *
 * Layout: toolbar sticky + matrice (permessi su righe, ruoli su colonne)
 * con gruppi collassabili, bulk toggle per gruppo, diff badge per ruolo
 * e floating save bar quando una o più colonne sono dirty.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';

import { useAuth } from '../../contexts/AuthContext';
import * as rbacApi from '../../lib/api/rbac';
import type { PermissionEntry, RoleDetail, RoleSummary } from '../../lib/api/rbac';
import { Callout, Hint } from '../ui';
import { FloatingSaveBar } from './roles/FloatingSaveBar';
import { GroupSection } from './roles/GroupSection';
import { RoleHeader } from './roles/RoleHeader';
import { RolesToolbar } from './roles/RolesToolbar';
import {
  computeDiff,
  dirtyRoleIds,
  filterPermissions,
  groupPermissions,
  isLocked,
} from './roles/utils';

type PermMap = Record<string, Set<string>>;

export function AdminRolesPage() {
  const { can } = useAuth();
  const canEdit = can('rbac.assign.admin');

  const [perms, setPerms] = useState<PermissionEntry[]>([]);
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [original, setOriginal] = useState<PermMap>({});
  const [draft, setDraft] = useState<PermMap>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const [query, setQuery] = useState('');
  const [onlyModified, setOnlyModified] = useState(false);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [permsList, rolesList] = await Promise.all([
        rbacApi.listPermissions(),
        rbacApi.listRoles(),
      ]);
      const details = await Promise.all(rolesList.map((r) => rbacApi.getRoleDetail(r.id)));
      const orig: PermMap = {};
      for (const d of details) orig[d.id] = new Set(d.permissions);
      setPerms(permsList);
      setRoles(rolesList);
      setOriginal(orig);
      setDraft(Object.fromEntries(Object.entries(orig).map(([k, v]) => [k, new Set(v)])));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'errore caricamento');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const togglePerm = useCallback(
    (roleId: string, slug: string) => {
      if (!canEdit) return;
      setDraft((d) => {
        const next = { ...d, [roleId]: new Set(d[roleId] ?? []) };
        if (next[roleId].has(slug)) next[roleId].delete(slug);
        else next[roleId].add(slug);
        return next;
      });
    },
    [canEdit],
  );

  const bulkSetGroup = useCallback(
    (roleId: string, slugs: string[], value: boolean) => {
      if (!canEdit) return;
      setDraft((d) => {
        const next = { ...d, [roleId]: new Set(d[roleId] ?? []) };
        for (const s of slugs) {
          if (value) next[roleId].add(s);
          else next[roleId].delete(s);
        }
        return next;
      });
    },
    [canEdit],
  );

  const dirtyIds = useMemo(
    () => dirtyRoleIds(roles, original, draft),
    [roles, original, draft],
  );
  const dirtyRoles = useMemo(
    () => roles.filter((r) => dirtyIds.includes(r.id)),
    [roles, dirtyIds],
  );

  const filteredPerms = useMemo(() => {
    let list = filterPermissions(perms, query);
    if (onlyModified) {
      const allChanged = new Set<string>();
      for (const rid of dirtyIds) {
        const d = computeDiff(original[rid] ?? new Set(), draft[rid] ?? new Set());
        for (const s of [...d.added, ...d.removed]) allChanged.add(s);
      }
      list = list.filter((p) => allChanged.has(p.slug));
    }
    return list;
  }, [perms, query, onlyModified, dirtyIds, original, draft]);

  const groups = useMemo(() => groupPermissions(filteredPerms), [filteredPerms]);

  const saveRole = useCallback(
    async (role: RoleSummary) => {
      const diff = computeDiff(original[role.id] ?? new Set(), draft[role.id] ?? new Set());
      if (diff.total === 0) return;
      setSaving((s) => new Set([...s, role.id]));
      try {
        const next = Array.from(draft[role.id] ?? []);
        const updated: RoleDetail = await rbacApi.setRolePermissions(role.id, next);
        setOriginal((o) => ({ ...o, [role.id]: new Set(updated.permissions) }));
        setDraft((d) => ({ ...d, [role.id]: new Set(updated.permissions) }));
        toast.success(`Ruolo ${role.slug}: ${diff.total} modifiche applicate`);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : 'salvataggio fallito');
      } finally {
        setSaving((s) => {
          const next = new Set(s);
          next.delete(role.id);
          return next;
        });
      }
    },
    [draft, original],
  );

  const resetRole = useCallback(
    (roleId: string) => {
      setDraft((d) => ({ ...d, [roleId]: new Set(original[roleId] ?? []) }));
    },
    [original],
  );

  const saveAll = useCallback(async () => {
    for (const r of dirtyRoles) {
      // serializza per evitare race conditions su token refresh
      await saveRole(r);
    }
  }, [dirtyRoles, saveRole]);

  const discardAll = useCallback(() => {
    setDraft(Object.fromEntries(Object.entries(original).map(([k, v]) => [k, new Set(v)])));
  }, [original]);

  const toggleCollapse = (id: string) =>
    setCollapsed((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  if (loading) return <div className="p-8 text-xs text-ink-subtle">Caricamento…</div>;

  return (
    <div className="relative flex flex-col">
      <RolesToolbar
        query={query}
        onQuery={setQuery}
        onlyModified={onlyModified}
        onToggleOnlyModified={() => setOnlyModified((v) => !v)}
        onExpandAll={() => setCollapsed(new Set())}
        onCollapseAll={() => setCollapsed(new Set(groups.map((g) => g.meta.id)))}
        permsCount={perms.length}
        filteredCount={filteredPerms.length}
        dirtyCount={dirtyIds.length}
      />

      {error && (
        <Callout tone="warning" className="m-5">
          {error}
        </Callout>
      )}
      {!canEdit && (
        <Callout tone="info" className="m-5">
          Visualizzazione sola lettura. Serve <code>rbac.assign.admin</code> per modificare.
        </Callout>
      )}

      {canEdit && roles.length > 0 && (
        <div className="px-5 pt-3">
          <Hint id="rbac.first_visit" tone="info" title="Come usare la matrice">
            Ogni colonna è un ruolo, ogni riga un permesso. Clicca sulla cella per togglare;
            il diff (+N / −M) appare nell’header del ruolo. Usa <strong>tutti</strong> nella riga
            di gruppo per assegnare l’intero blocco. <code>superuser</code> è protetto a livello
            backend.
          </Hint>
        </div>
      )}

      <div className="overflow-auto">
        <table className="w-full border-separate border-spacing-0 text-xs">
          <thead>
            <tr>
              <th
                scope="col"
                className="sticky left-0 top-[44px] z-30 border-b border-r border-[var(--color-border)] bg-[var(--color-canvas)] px-4 py-2 text-left text-[10px] uppercase tracking-wide text-ink-subtle"
                style={{ minWidth: 280 }}
              >
                Permesso
              </th>
              {roles.map((r) => {
                const diff = computeDiff(
                  original[r.id] ?? new Set(),
                  draft[r.id] ?? new Set(),
                );
                return (
                  <RoleHeader
                    key={r.id}
                    role={r}
                    totalGranted={draft[r.id]?.size ?? 0}
                    totalAvailable={perms.length}
                    diff={diff}
                    locked={isLocked(r)}
                    canEdit={canEdit}
                    saving={saving.has(r.id)}
                    onSave={() => saveRole(r)}
                    onReset={() => resetRole(r.id)}
                  />
                );
              })}
            </tr>
          </thead>
          <tbody>
            {groups.length === 0 && (
              <tr>
                <td
                  colSpan={roles.length + 1}
                  className="px-5 py-8 text-center text-[11px] text-ink-subtle"
                >
                  {onlyModified
                    ? 'Nessuna modifica attiva.'
                    : query
                      ? `Nessun permesso corrisponde a “${query}”.`
                      : 'Nessun permesso disponibile.'}
                </td>
              </tr>
            )}
            {groups.map((g) => (
              <GroupSection
                key={g.meta.id}
                group={g.meta}
                perms={g.perms}
                roles={roles}
                draft={draft}
                original={original}
                collapsed={collapsed.has(g.meta.id)}
                canEdit={canEdit}
                onToggleCollapse={() => toggleCollapse(g.meta.id)}
                onTogglePerm={togglePerm}
                onBulkSetGroup={bulkSetGroup}
                isLocked={isLocked}
              />
            ))}
          </tbody>
        </table>
      </div>

      <FloatingSaveBar
        dirtyRoles={dirtyRoles}
        saving={saving.size > 0}
        onSaveAll={saveAll}
        onDiscardAll={discardAll}
      />

      <p className="border-t border-[var(--color-border)] px-5 py-3 text-[11px] text-ink-subtle">
        Le modifiche prendono effetto immediato per nuove sessioni. Gli utenti già loggati
        rinfrescano i permessi al prossimo refresh token.
      </p>
    </div>
  );
}
