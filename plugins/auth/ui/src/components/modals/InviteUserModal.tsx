/** Admin modal to invite a user by email (they set their own password). */

import { useState, type FormEvent } from 'react';
import { X, Mail } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { inviteUser } from '../../api/invitations';

const ROLE_OPTIONS = ['user', 'admin', 'guest'];

export default function InviteUserModal({
  onClose,
  onInvited,
}: {
  onClose: () => void;
  onInvited: () => void;
}) {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [roles, setRoles] = useState<string[]>(['user']);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const toggleRole = (r: string) =>
    setRoles((cur) => (cur.includes(r) ? cur.filter((x) => x !== r) : [...cur, r]));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await inviteUser(email, roles.length ? roles : ['user']);
      onInvited();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('users.invite.error'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <h3>
            <Mail size={18} /> {t('users.invite.title')}
          </h3>
          <button className="admin-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <form onSubmit={submit} className="admin-modal-body">
          {error && <div className="admin-alert admin-alert-error">{error}</div>}
          <p className="admin-hint">{t('users.invite.desc')}</p>
          <label className="admin-field">
            <span>{t('users.invite.email')}</span>
            <input
              type="email"
              className="admin-input"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="person@example.com"
              autoFocus
            />
          </label>
          <div className="admin-field">
            <span>{t('users.invite.roles')}</span>
            <div className="invite-roles">
              {ROLE_OPTIONS.map((r) => (
                <label key={r} className="invite-role">
                  <input
                    type="checkbox"
                    checked={roles.includes(r)}
                    onChange={() => toggleRole(r)}
                  />{' '}
                  {r}
                </label>
              ))}
            </div>
          </div>
          <div className="admin-modal-actions">
            <button type="button" className="admin-btn admin-btn-ghost" onClick={onClose}>
              {t('common.cancel')}
            </button>
            <button type="submit" className="admin-btn admin-btn-primary" disabled={busy || !email}>
              {busy ? t('users.invite.sending') : t('users.invite.send')}
            </button>
          </div>
        </form>
      </div>
      <style>{`
        .invite-roles { display: flex; gap: 1rem; flex-wrap: wrap; }
        .invite-role { display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; text-transform: capitalize; cursor: pointer; }
      `}</style>
    </div>
  );
}
