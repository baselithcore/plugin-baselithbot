/**
 * UserDangerZone — sezione "Operazioni" nel UserDetailPanel.
 *
 * Espone disattivazione (toggle reversibile, preserva dati) + hard
 * delete (cascade su conversations / memories / role grants / group
 * memberships, traccia anonimizzata in audit_events).
 *
 * Gating client-side specchio del backend:
 * - self-action disabilitata (no auto-deactivate / auto-delete)
 * - bottoni disabilitati durante l'operazione (`busy`)
 *
 * Server-side enforce inoltre "ultimo superuser attivo" — un 409
 * arrivato qui viene mostrato come toast esplicito senza assumerlo.
 */

import { Power, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';

import * as rbacApi from '../../../lib/api/rbac';
import type { UserWithRoles } from '../../../lib/api/rbac';
import { Button, Callout } from '../../ui';

interface Props {
  user: UserWithRoles;
  currentUserId: string | null;
  onChanged: () => void | Promise<void>;
  onDeleted: () => void;
}

export function UserDangerZone({ user, currentUserId, onChanged, onDeleted }: Props) {
  const [busy, setBusy] = useState<'toggle' | 'delete' | null>(null);
  const isSelf = currentUserId === user.id;

  const toggleActive = async () => {
    setBusy('toggle');
    try {
      await rbacApi.setUserActive(user.id, !user.is_active);
      toast.success(user.is_active ? 'Utente disattivato' : 'Utente attivato');
      await onChanged();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'operazione fallita');
    } finally {
      setBusy(null);
    }
  };

  const deleteUser = async () => {
    if (
      !window.confirm(
        `Cancellare DEFINITIVAMENTE "${user.email}"?\n\n` +
          'Verranno rimossi: conversazioni, memorie, feedback, ruoli, ' +
          'membership gruppi. Le righe di audit restano (con user_id NULL).'
      )
    ) {
      return;
    }
    setBusy('delete');
    try {
      await rbacApi.deleteUser(user.id);
      toast.success(`"${user.email}" eliminato`);
      onDeleted();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'eliminazione fallita');
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="mt-5 flex flex-col gap-2 border-t border-[var(--color-border)] pt-4">
      <div className="text-[10px] uppercase font-semibold text-ink-subtle">Operazioni</div>
      {isSelf && (
        <Callout tone="info">
          Non puoi disattivare o cancellare il tuo stesso account da qui.
        </Callout>
      )}
      <div className="flex flex-col gap-1.5">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => void toggleActive()}
          disabled={isSelf || busy === 'toggle'}
        >
          <Power size={12} />
          {user.is_active ? 'Disattiva accesso' : 'Riattiva accesso'}
        </Button>
        <p className="text-[10px] text-ink-subtle">
          Disattivare blocca il login senza cancellare dati. Reversibile.
        </p>
      </div>
      <div className="mt-2 flex flex-col gap-1.5">
        <Button
          type="button"
          variant="danger"
          size="sm"
          onClick={() => void deleteUser()}
          disabled={isSelf || busy === 'delete'}
        >
          <Trash2 size={12} />
          Elimina utente
        </Button>
        <p className="text-[10px] text-ink-subtle">
          Cancellazione definitiva. Cascade su conversations, memorie, ruoli, group membership.
          Audit log preservato (anonimizzato).
        </p>
      </div>
    </section>
  );
}
