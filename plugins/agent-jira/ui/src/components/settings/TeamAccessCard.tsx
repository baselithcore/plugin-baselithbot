import type { Dispatch, FormEvent, SetStateAction } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  Shield,
  ShieldCheck,
  UserCheck,
  UserPlus,
  UserX,
  Users,
} from 'lucide-react';
import type { AuthUser } from '../../types';
import { SectionCard } from './SettingsPrimitives';
import { formatDate } from './utils';

type InviteFormState = {
  email: string;
  password: string;
  name: string;
  role: string;
};

type Props = {
  currentUser: AuthUser;
  canManageTeam: boolean;
  canInvite: boolean;
  loading: boolean;
  error: string | null;
  inviteMsg: { ok: boolean; text: string } | null;
  inviting: boolean;
  maxUsers: number;
  teamCount: number;
  teamMembers: AuthUser[];
  showInvite: boolean;
  inviteForm: InviteFormState;
  onToggleInvite: () => void;
  onInviteSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onInviteFormChange: Dispatch<SetStateAction<InviteFormState>>;
  onToggleRole: (user: AuthUser) => void;
  onToggleActive: (user: AuthUser) => void;
};

const TeamAccessCard = ({
  currentUser,
  canManageTeam,
  canInvite,
  loading,
  error,
  inviteMsg,
  inviting,
  maxUsers,
  teamCount,
  teamMembers,
  showInvite,
  inviteForm,
  onToggleInvite,
  onInviteSubmit,
  onInviteFormChange,
  onToggleRole,
  onToggleActive,
}: Props) => (
  <SectionCard
    title="Team e accessi"
    description="Utenti del workspace, inviti e permessi amministrativi."
    icon={<Users size={18} />}
    className="settings-card--full"
    action={
      canManageTeam && canInvite ? (
        <button className="settings-btn settings-btn--secondary" onClick={onToggleInvite}>
          <UserPlus size={15} />
          {showInvite ? 'Chiudi invito' : 'Invita utente'}
        </button>
      ) : null
    }
  >
    <div className="settings-team-overview">
      <div>
        <strong>{canManageTeam ? `${teamCount}/${maxUsers} utenti` : 'Account singolo'}</strong>
        <p>
          {canManageTeam
            ? 'Gestisci il team senza uscire da questa pagina.'
            : 'Il piano attuale non prevede più utenti amministrabili dalla console.'}
        </p>
      </div>
      {!canManageTeam ? (
        <span className="settings-status-pill settings-status-pill--neutral">
          <ShieldCheck size={12} />
          Solo workspace owner
        </span>
      ) : null}
    </div>

    {showInvite && canInvite ? (
      <form className="settings-invite-panel" onSubmit={onInviteSubmit}>
        <div className="settings-form-grid">
          <label className="settings-field">
            <span>Email</span>
            <input
              className="settings-input"
              type="email"
              placeholder="nome@azienda.it"
              value={inviteForm.email}
              onChange={(event) =>
                onInviteFormChange((current) => ({ ...current, email: event.target.value }))
              }
              required
            />
          </label>
          <label className="settings-field">
            <span>Nome</span>
            <input
              className="settings-input"
              type="text"
              placeholder="Nome visualizzato"
              value={inviteForm.name}
              onChange={(event) =>
                onInviteFormChange((current) => ({ ...current, name: event.target.value }))
              }
            />
          </label>
          <label className="settings-field">
            <span>Password iniziale</span>
            <input
              className="settings-input"
              type="password"
              placeholder="Minimo 8 caratteri"
              value={inviteForm.password}
              onChange={(event) =>
                onInviteFormChange((current) => ({ ...current, password: event.target.value }))
              }
              minLength={8}
              required
            />
          </label>
          <label className="settings-field">
            <span>Ruolo</span>
            <select
              className="settings-select"
              value={inviteForm.role}
              onChange={(event) =>
                onInviteFormChange((current) => ({ ...current, role: event.target.value }))
              }
            >
              <option value="user">Utente</option>
              <option value="admin">Admin</option>
            </select>
          </label>
        </div>
        <div className="settings-form-actions">
          <button className="settings-btn settings-btn--primary" type="submit" disabled={inviting}>
            {inviting ? <Loader2 size={15} className="ws-spin" /> : <UserPlus size={15} />}
            {inviting ? 'Creazione in corso...' : 'Crea utente'}
          </button>
        </div>
      </form>
    ) : null}

    {inviteMsg ? (
      <div
        className={`settings-feedback ${
          inviteMsg.ok ? 'settings-feedback--ok' : 'settings-feedback--error'
        }`}
      >
        {inviteMsg.ok ? <CheckCircle2 size={15} /> : <AlertCircle size={15} />}
        <span>{inviteMsg.text}</span>
      </div>
    ) : null}

    {error ? (
      <div className="settings-feedback settings-feedback--error">
        <AlertCircle size={15} />
        <span>{error}</span>
      </div>
    ) : null}

    {loading ? (
      <div className="settings-loading-state">
        <Loader2 size={16} className="ws-spin" />
        Caricamento accessi...
      </div>
    ) : (
      <div className="settings-members-list">
        {teamMembers.map((user) => {
          const active = user.is_active !== false;
          return (
            <div
              key={user.id}
              className={`settings-member-row ${active ? '' : 'settings-member-row--inactive'}`}
            >
              <div className="settings-member-id">
                <span className="settings-member-avatar">
                  {(user.display_name || user.email).slice(0, 1).toUpperCase()}
                </span>
                <div>
                  <div className="settings-member-name">
                    {user.display_name || user.email.split('@')[0]}
                    {user.id === currentUser.id ? (
                      <span className="settings-self-chip">tu</span>
                    ) : null}
                  </div>
                  <div className="settings-member-email">{user.email}</div>
                </div>
              </div>

              <div className="settings-member-meta">
                <span
                  className={`settings-status-pill ${
                    user.role === 'admin'
                      ? 'settings-status-pill--ok'
                      : 'settings-status-pill--neutral'
                  }`}
                >
                  {user.role === 'admin' ? <ShieldCheck size={12} /> : <Shield size={12} />}
                  {user.role === 'admin' ? 'Admin' : 'Utente'}
                </span>
                <span
                  className={`settings-status-pill ${
                    active ? 'settings-status-pill--ok' : 'settings-status-pill--warn'
                  }`}
                >
                  {active ? <UserCheck size={12} /> : <UserX size={12} />}
                  {active ? 'Attivo' : 'Sospeso'}
                </span>
                <span className="settings-member-login">
                  Ultimo accesso {formatDate(user.last_login_at)}
                </span>
              </div>

              {canManageTeam && user.id !== currentUser.id ? (
                <div className="settings-member-actions">
                  <button
                    className="settings-icon-btn"
                    onClick={() => onToggleRole(user)}
                    title={user.role === 'admin' ? 'Rimuovi permessi admin' : 'Rendi admin'}
                  >
                    {user.role === 'admin' ? <Shield size={14} /> : <ShieldCheck size={14} />}
                  </button>
                  <button
                    className="settings-icon-btn"
                    onClick={() => onToggleActive(user)}
                    title={active ? 'Disattiva utente' : 'Riattiva utente'}
                  >
                    {active ? <UserX size={14} /> : <UserCheck size={14} />}
                  </button>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    )}
  </SectionCard>
);

export default TeamAccessCard;
