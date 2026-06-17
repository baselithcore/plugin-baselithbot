/** Pending-invitations strip for the Users tab. Hidden when there are none. */

import { useCallback, useEffect, useState } from 'react';
import { Mail, X, Clock } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { listInvitations, revokeInvitation, type Invitation } from '../../api/invitations';

export default function InvitationsPanel({ refreshKey }: { refreshKey: number }) {
  const { t } = useTranslation();
  const [invites, setInvites] = useState<Invitation[]>([]);

  const load = useCallback(() => {
    listInvitations()
      .then((all) => setInvites(all.filter((i) => !i.accepted_at)))
      .catch(() => setInvites([]));
  }, []);

  useEffect(load, [load, refreshKey]);

  const revoke = async (id: string) => {
    if (!window.confirm(t('users.invite.confirmRevoke'))) return;
    try {
      await revokeInvitation(id);
      load();
    } catch {
      /* surfaced via reload */
    }
  };

  if (invites.length === 0) return null;

  return (
    <div className="admin-card invitations-panel">
      <h3 className="invitations-title">
        <Mail size={15} /> {t('users.invite.pending', { count: invites.length })}
      </h3>
      <ul className="invitations-list">
        {invites.map((i) => (
          <li key={i.id} className="invitations-row">
            <div>
              <strong>{i.email}</strong>
              <span className="invitations-meta">
                {i.roles.join(', ')}
                {i.expires_at &&
                  ` · ${t('users.invite.expires', { date: new Date(i.expires_at).toLocaleDateString() })}`}
              </span>
            </div>
            <span className="invitations-status">
              <Clock size={12} /> {t('users.invite.statusPending')}
            </span>
            <button
              className="admin-btn admin-btn-ghost admin-btn-icon"
              onClick={() => revoke(i.id)}
              title={t('users.invite.revoke')}
            >
              <X size={15} />
            </button>
          </li>
        ))}
      </ul>
      <style>{`
        .invitations-panel { padding: 1rem 1.25rem; }
        .invitations-title { display: flex; align-items: center; gap: 0.4rem; font-size: 0.9rem; font-weight: 600; margin: 0 0 0.75rem; }
        .invitations-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.5rem; }
        .invitations-row { display: flex; align-items: center; gap: 1rem; padding: 0.55rem 0; border-top: 1px solid var(--admin-table-border, rgba(255,255,255,0.06)); }
        .invitations-row:first-child { border-top: none; }
        .invitations-row > div:first-child { flex: 1; }
        .invitations-row strong { font-size: 0.85rem; }
        .invitations-meta { display: block; font-size: 0.74rem; color: var(--admin-text-muted, #94a3b8); margin-top: 0.15rem; }
        .invitations-status { display: inline-flex; align-items: center; gap: 0.3rem; font-size: 0.72rem; color: #fbbf24; }
      `}</style>
    </div>
  );
}
