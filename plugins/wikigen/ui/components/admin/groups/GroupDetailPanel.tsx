/**
 * GroupDetailPanel — drawer destro per gestire membri + ruoli del gruppo.
 *
 * Membership e ruoli sono indipendenti: aggiungere un ruolo NON aggiunge
 * automaticamente i membri attuali al ruolo (era già loro tramite gruppo —
 * il ruolo è proprietà del gruppo). Rimuovere un utente dal gruppo gli
 * toglie SOLO i perms ereditati via questo gruppo (altri gruppi + ruoli
 * diretti restano).
 */

import { Trash2, UserPlus2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';

import * as groupsApi from '../../../lib/api/groups';
import type { GroupDetail } from '../../../lib/api/groups';
import type { RoleSummary, UserWithRoles } from '../../../lib/api/rbac';

interface Props {
  groupId: string;
  allRoles: RoleSummary[];
  allUsers: UserWithRoles[];
  canAssignRole: (slug: string, isSystem: boolean) => boolean;
  onChanged: () => void;
}

export function GroupDetailPanel({ groupId, allRoles, allUsers, canAssignRole, onChanged }: Props) {
  const [detail, setDetail] = useState<GroupDetail | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const d = await groupsApi.getGroup(groupId);
      setDetail(d);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'caricamento gruppo fallito');
    }
  }, [groupId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const removeMember = useCallback(
    async (userId: string) => {
      setBusy(`rm-mem:${userId}`);
      try {
        await groupsApi.removeMember(groupId, userId);
        await reload();
        onChanged();
        toast.success('Membro rimosso');
      } catch (e) {
        toast.error(e instanceof Error ? e.message : 'rimozione fallita');
      } finally {
        setBusy(null);
      }
    },
    [groupId, onChanged, reload]
  );

  const addMember = useCallback(
    async (userId: string) => {
      setBusy(`add-mem:${userId}`);
      try {
        const res = await groupsApi.addMembers(groupId, [userId]);
        await reload();
        onChanged();
        if (res.added.length > 0) toast.success('Membro aggiunto');
        else toast.message('Già membro o cross-tenant', { description: 'no-op' });
      } catch (e) {
        toast.error(e instanceof Error ? e.message : 'aggiunta fallita');
      } finally {
        setBusy(null);
      }
    },
    [groupId, onChanged, reload]
  );

  const toggleRole = useCallback(
    async (role: RoleSummary) => {
      if (!detail) return;
      const has = detail.roles.some((r) => r.id === role.id);
      setBusy(`role:${role.id}`);
      try {
        if (has) await groupsApi.revokeGroupRole(groupId, role.id);
        else await groupsApi.assignGroupRole(groupId, role.id);
        await reload();
        onChanged();
        toast.success(has ? `Revocato ${role.slug}` : `Assegnato ${role.slug}`);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : 'operazione ruolo fallita');
      } finally {
        setBusy(null);
      }
    },
    [detail, groupId, onChanged, reload]
  );

  if (!detail) {
    return (
      <aside className="w-80 border-l border-[var(--color-border)] p-5 text-xs text-ink-subtle">
        Caricamento…
      </aside>
    );
  }

  const memberIds = new Set(detail.members.map((m) => m.id));
  const sameTenantUsers = allUsers.filter((u) => u.tenant_id === detail.tenant_id);
  const candidates = sameTenantUsers.filter((u) => !memberIds.has(u.id));

  return (
    <aside className="flex w-96 flex-col border-l border-[var(--color-border)] overflow-y-auto">
      <header className="border-b border-[var(--color-border)] px-5 py-3">
        <div className="text-[10px] uppercase text-ink-subtle">Gruppo</div>
        <div className="text-sm font-semibold">{detail.name}</div>
        <div className="text-[11px] text-ink-subtle font-mono">{detail.slug}</div>
        {detail.description && (
          <p className="mt-2 text-[11px] text-ink-subtle">{detail.description}</p>
        )}
      </header>

      <section className="border-b border-[var(--color-border)] px-5 py-3">
        <h3 className="mb-2 text-[10px] font-semibold uppercase text-ink-subtle">
          Membri ({detail.members.length})
        </h3>
        <ul className="space-y-1.5">
          {detail.members.map((m) => (
            <li key={m.id} className="flex items-center justify-between gap-2 text-xs">
              <div className="min-w-0 flex-1">
                <div className="truncate">{m.email}</div>
                {m.display_name && (
                  <div className="truncate text-[10px] text-ink-subtle">{m.display_name}</div>
                )}
              </div>
              <button
                type="button"
                className="btn-ghost text-danger"
                onClick={() => void removeMember(m.id)}
                disabled={busy === `rm-mem:${m.id}`}
                aria-label={`Rimuovi ${m.email}`}
              >
                <Trash2 size={12} />
              </button>
            </li>
          ))}
          {detail.members.length === 0 && (
            <li className="text-[11px] text-ink-subtle">Nessun membro.</li>
          )}
        </ul>
        {candidates.length > 0 && (
          <details className="mt-3 text-xs">
            <summary className="cursor-pointer text-ink-subtle">
              <UserPlus2 size={11} className="mr-1 inline" />
              Aggiungi membro ({candidates.length} disponibili)
            </summary>
            <ul className="mt-2 max-h-48 overflow-y-auto space-y-1">
              {candidates.map((u) => (
                <li key={u.id}>
                  <button
                    type="button"
                    className="w-full text-left rounded px-1.5 py-1 hover:bg-[var(--color-surface-hover)]"
                    onClick={() => void addMember(u.id)}
                    disabled={busy === `add-mem:${u.id}`}
                  >
                    {u.email}
                  </button>
                </li>
              ))}
            </ul>
          </details>
        )}
      </section>

      <section className="px-5 py-3">
        <h3 className="mb-2 text-[10px] font-semibold uppercase text-ink-subtle">
          Ruoli ({detail.roles.length})
        </h3>
        <ul className="space-y-1">
          {allRoles.map((r) => {
            const has = detail.roles.some((x) => x.id === r.id);
            const allowed = canAssignRole(r.slug, r.is_system);
            return (
              <li key={r.id}>
                <label
                  className="flex items-center gap-2 text-xs cursor-pointer rounded px-1.5 py-1 hover:bg-[var(--color-surface-hover)]"
                  title={
                    !allowed
                      ? `Manca rbac.assign.${r.slug} — non puoi gestire questo ruolo`
                      : undefined
                  }
                >
                  <input
                    type="checkbox"
                    checked={has}
                    disabled={!allowed || busy === `role:${r.id}`}
                    onChange={() => void toggleRole(r)}
                  />
                  <span className="font-mono">{r.slug}</span>
                  {r.is_system && (
                    <span className="ml-auto text-[9px] text-ink-subtle uppercase">system</span>
                  )}
                </label>
              </li>
            );
          })}
        </ul>
      </section>
    </aside>
  );
}
