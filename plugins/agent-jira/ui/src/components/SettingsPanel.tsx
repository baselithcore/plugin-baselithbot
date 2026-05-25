import { useCallback, useEffect, useState, type FormEvent } from 'react';
import {
  Activity,
  AlertCircle,
  Building2,
  Check,
  CheckCircle2,
  Copy,
  FolderKanban,
  Globe,
  HardDrive,
  KeyRound,
  Link2,
  Loader2,
  Mail,
  Monitor,
  RefreshCcw,
  Settings,
  ShieldCheck,
  User,
  Users,
} from 'lucide-react';
import pkg from '../../package.json';
import {
  fetchJiraSettings,
  fetchSystemHealth,
  inviteUser,
  listUsers,
  updateUserAdmin,
  type SystemHealthResponse,
} from '../api/client';
import type { AuthUser, JiraSettings } from '../types';
import SettingsOverview from './settings/SettingsOverview';
import TeamAccessCard from './settings/TeamAccessCard';
import { DetailTile, SectionCard } from './settings/SettingsPrimitives';
import { formatDate, getErrorMessage, truncateMiddle } from './settings/utils';

type Props = {
  currentUser: AuthUser;
  maxUsers?: number;
  onLogout: () => void;
  onOpenJiraWizard?: () => void;
};
type InviteFormState = {
  email: string;
  password: string;
  name: string;
  role: string;
};
const EMPTY_INVITE_FORM: InviteFormState = { email: '', password: '', name: '', role: 'user' };

const SettingsPanel = ({ currentUser, maxUsers = 1, onLogout, onOpenJiraWizard }: Props) => {
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [userError, setUserError] = useState<string | null>(null);
  const [jiraSettings, setJiraSettings] = useState<JiraSettings | null>(null);
  const [loadingJira, setLoadingJira] = useState(false);
  const [jiraConfigurable, setJiraConfigurable] = useState(false);
  const [systemHealth, setSystemHealth] = useState<SystemHealthResponse | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [copiedId, setCopiedId] = useState(false);
  const [showInvite, setShowInvite] = useState(false);
  const [inviteForm, setInviteForm] = useState<InviteFormState>(EMPTY_INVITE_FORM);
  const [inviting, setInviting] = useState(false);
  const [inviteMsg, setInviteMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const isAdmin = currentUser.role === 'admin';
  const canManageTeam = isAdmin && maxUsers > 1;
  const roleLabel = canManageTeam ? 'Admin workspace' : 'Proprietario';
  const roleHelper = canManageTeam
    ? 'Gestisci utenti, permessi e integrazioni'
    : 'Workspace in modalità single-account';
  const clientInfo = {
    browser: (() => {
      const ua = typeof navigator !== 'undefined' ? navigator.userAgent : '';
      if (ua.includes('Edg')) return 'Edge';
      if (ua.includes('Firefox')) return 'Firefox';
      if (ua.includes('Chrome')) return 'Chrome';
      if (ua.includes('Safari')) return 'Safari';
      return 'Browser generico';
    })(),
    os: (() => {
      const ua = typeof navigator !== 'undefined' ? navigator.userAgent : '';
      if (ua.includes('Win')) return 'Windows';
      if (ua.includes('Mac')) return 'macOS';
      if (ua.includes('Linux')) return 'Linux';
      return 'Sistema generico';
    })(),
  };
  const loadUsers = useCallback(() => {
    if (!canManageTeam) {
      setUsers([{ ...currentUser, is_active: true }]);
      setLoadingUsers(false);
      return;
    }

    setLoadingUsers(true);
    listUsers()
      .then((res) => {
        setUsers(res.users);
        setUserError(null);
      })
      .catch((error) => setUserError(getErrorMessage(error, 'Impossibile caricare il team.')))
      .finally(() => setLoadingUsers(false));
  }, [canManageTeam, currentUser]);

  const loadJira = useCallback(() => {
    setLoadingJira(true);
    fetchJiraSettings()
      .then((res) => {
        setJiraSettings(res.settings);
        setJiraConfigurable(res.configurable);
      })
      .catch(() => {
        setJiraSettings(null);
        setJiraConfigurable(false);
      })
      .finally(() => setLoadingJira(false));
  }, []);

  const loadHealth = useCallback(() => {
    setLoadingHealth(true);
    fetchSystemHealth()
      .then(setSystemHealth)
      .catch(() => setSystemHealth(null))
      .finally(() => setLoadingHealth(false));
  }, []);
  useEffect(() => {
    loadUsers();
    loadJira();
    loadHealth();
  }, [loadUsers, loadJira, loadHealth]);

  const handleCopyId = async (id: string) => {
    if (!id || !navigator.clipboard) return;
    try {
      await navigator.clipboard.writeText(id);
      setCopiedId(true);
      window.setTimeout(() => setCopiedId(false), 1800);
    } catch {
      setCopiedId(false);
    }
  };
  const handleInvite = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!inviteForm.email.includes('@') || inviteForm.password.length < 8) return;

    setInviting(true);
    setInviteMsg(null);
    try {
      await inviteUser({
        email: inviteForm.email,
        password: inviteForm.password,
        display_name: inviteForm.name,
        role: inviteForm.role,
      });
      setInviteMsg({ ok: true, text: `Utente ${inviteForm.email} creato correttamente.` });
      setInviteForm(EMPTY_INVITE_FORM);
      setShowInvite(false);
      loadUsers();
    } catch (error) {
      setInviteMsg({
        ok: false,
        text: getErrorMessage(error, 'Creazione utente non riuscita.'),
      });
    } finally {
      setInviting(false);
    }
  };
  const handleToggleActive = async (user: AuthUser) => {
    if (user.id === currentUser.id) return;
    try {
      await updateUserAdmin(user.id, { is_active: !user.is_active });
      loadUsers();
    } catch (error) {
      setUserError(getErrorMessage(error, 'Aggiornamento stato utente non riuscito.'));
    }
  };
  const handleToggleRole = async (user: AuthUser) => {
    if (user.id === currentUser.id) return;
    const newRole = user.role === 'admin' ? 'user' : 'admin';
    try {
      await updateUserAdmin(user.id, { role: newRole });
      loadUsers();
    } catch (error) {
      setUserError(getErrorMessage(error, 'Aggiornamento ruolo non riuscito.'));
    }
  };
  const dependencies = systemHealth?.dependencies ? Object.values(systemHealth.dependencies) : [];
  const readyDependencies = dependencies.filter((dep) => dep.ready).length;
  const totalDependencies = dependencies.length;
  const healthHealthy = totalDependencies > 0 && readyDependencies === totalDependencies;
  const jiraReady = Boolean(jiraSettings?.api_token_set);
  const teamMembers = canManageTeam ? users : [{ ...currentUser, is_active: true }];
  const teamCount = canManageTeam ? users.length : 1;
  const canInvite = canManageTeam && users.length < maxUsers;
  const jiraProjects = jiraSettings?.allowed_project_keys?.length
    ? jiraSettings.allowed_project_keys.length
    : jiraSettings?.default_project_key || jiraSettings?.project_key
      ? 1
      : 0;

  return (
    <div className="settings-layout">
      <div className="settings-page">
        <SettingsOverview
          currentUser={currentUser}
          roleLabel={roleLabel}
          roleHelper={roleHelper}
          jiraReady={jiraReady}
          jiraProjects={jiraProjects}
          jiraConfigurable={jiraConfigurable}
          totalDependencies={totalDependencies}
          readyDependencies={readyDependencies}
          healthHealthy={healthHealthy}
          canManageTeam={canManageTeam}
          teamCount={teamCount}
          maxUsers={maxUsers}
          onLogout={onLogout}
          onOpenJiraWizard={onOpenJiraWizard}
        />

        <div className="settings-dashboard">
          <SectionCard
            title="Profilo e workspace"
            description="Dati principali dell'account e contesto del tenant."
            icon={<User size={18} />}
            className="settings-card--wide"
          >
            <div className="settings-detail-grid">
              <DetailTile
                label="Nome visualizzato"
                value={currentUser.display_name || 'Non impostato'}
                icon={<User size={14} />}
                hint="Nome mostrato nella console."
              />
              <DetailTile
                label="Email"
                value={currentUser.email}
                icon={<Mail size={14} />}
                hint="Usata per autenticazione e notifiche di accesso."
              />
              <DetailTile
                label="Ruolo"
                value={roleLabel}
                icon={<ShieldCheck size={14} />}
                hint={roleHelper}
              />
              <DetailTile
                label="Tenant"
                value={
                  currentUser.tenant_id ? truncateMiddle(currentUser.tenant_id) : 'Non assegnato'
                }
                icon={<Building2 size={14} />}
                hint="Identificativo workspace condiviso con Jira e servizi backend."
                mono
              />
            </div>
          </SectionCard>

          <SectionCard
            title="Integrazione Jira"
            description="Connessione, progetto predefinito e provenienza delle credenziali."
            icon={<Link2 size={18} />}
            action={
              jiraConfigurable && onOpenJiraWizard ? (
                <button className="settings-btn settings-btn--secondary" onClick={onOpenJiraWizard}>
                  <Settings size={15} />
                  Apri wizard
                </button>
              ) : null
            }
          >
            {loadingJira ? (
              <div className="settings-loading-state">
                <Loader2 size={16} className="ws-spin" />
                Caricamento impostazioni Jira...
              </div>
            ) : jiraSettings ? (
              <>
                <div
                  className={`settings-inline-banner ${
                    jiraReady ? 'settings-inline-banner--ok' : 'settings-inline-banner--warn'
                  }`}
                >
                  {jiraReady ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                  <div>
                    <strong>
                      {jiraReady ? 'Connessione pronta' : 'Configurazione incompleta'}
                    </strong>
                    <span>
                      {jiraReady
                        ? 'Token presente e progetto pronto all’uso.'
                        : 'Completa token o progetto per abilitare la sincronizzazione.'}
                    </span>
                  </div>
                </div>

                <div className="settings-detail-grid">
                  <DetailTile
                    label="Endpoint"
                    value={jiraSettings.base_url || 'Non configurato'}
                    icon={<Globe size={14} />}
                    hint="URL del tenant Atlassian collegato."
                  />
                  <DetailTile
                    label="Utente collegato"
                    value={jiraSettings.email || 'Non configurato'}
                    icon={<Mail size={14} />}
                    hint="Account Jira usato per creare issue e sincronizzazioni."
                  />
                  <DetailTile
                    label="Token API"
                    value={jiraSettings.api_token_set ? 'Configurato' : 'Mancante'}
                    icon={<KeyRound size={14} />}
                    hint="Le credenziali sensibili non vengono mai mostrate in chiaro."
                  />
                  <DetailTile
                    label="Progetto predefinito"
                    value={jiraSettings.default_project_key || jiraSettings.project_key || '—'}
                    icon={<FolderKanban size={14} />}
                    hint="Chiave usata come default per story e test case."
                    mono
                  />
                  <DetailTile
                    label="Progetti autorizzati"
                    value={
                      jiraSettings.allowed_project_keys?.length
                        ? jiraSettings.allowed_project_keys.join(', ')
                        : jiraSettings.default_project_key || jiraSettings.project_key || '—'
                    }
                    icon={<FolderKanban size={14} />}
                    hint="Elenco dei progetti disponibili nella console."
                    mono
                  />
                  <DetailTile
                    label="Origine configurazione"
                    value={
                      jiraSettings.source === 'environment'
                        ? 'Variabili ambiente'
                        : 'Configurazione tenant'
                    }
                    icon={<Settings size={14} />}
                    hint={
                      jiraSettings.source === 'environment'
                        ? 'Gestita fuori dalla UI.'
                        : 'Configurabile dal wizard della console.'
                    }
                  />
                </div>
              </>
            ) : (
              <div className="settings-empty-state">
                <AlertCircle size={16} />
                <span>Impossibile caricare le impostazioni Jira.</span>
              </div>
            )}
          </SectionCard>

          <SectionCard
            title="Sistema e diagnostica"
            description="Stato dei servizi richiesti per ricerca, grafo e integrazione Jira."
            icon={<Activity size={18} />}
            action={
              <button
                className="settings-btn settings-btn--secondary"
                onClick={loadHealth}
                disabled={loadingHealth}
              >
                <RefreshCcw size={15} className={loadingHealth ? 'ws-spin' : ''} />
                Aggiorna
              </button>
            }
          >
            {loadingHealth && !systemHealth ? (
              <div className="settings-loading-state">
                <Loader2 size={16} className="ws-spin" />
                Verifica servizi in corso...
              </div>
            ) : dependencies.length > 0 ? (
              <div className="settings-health-list">
                {dependencies.map((dependency) => {
                  const tone = !dependency.enabled ? 'neutral' : dependency.ready ? 'ok' : 'warn';
                  const label = !dependency.enabled
                    ? 'Disabilitato'
                    : dependency.ready
                      ? 'Ready'
                      : 'Degraded';

                  return (
                    <div key={dependency.name} className="settings-health-row">
                      <div className="settings-health-main">
                        <span className="settings-health-name">{dependency.name}</span>
                        <span className="settings-health-meta">
                          {dependency.required ? 'Richiesto' : 'Opzionale'}
                        </span>
                      </div>
                      <div className="settings-health-side">
                        <span className={`settings-status-pill settings-status-pill--${tone}`}>
                          {tone === 'ok' ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
                          {label}
                        </span>
                        <span className="settings-health-detail">
                          {dependency.error || dependency.status || 'Nessun dettaglio disponibile'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="settings-empty-state">
                <AlertCircle size={16} />
                <span>Nessun dato diagnostico disponibile.</span>
              </div>
            )}
          </SectionCard>

          <SectionCard
            title="Sessione e client"
            description="Dettagli utili per supporto operativo e troubleshooting locale."
            icon={<Monitor size={18} />}
          >
            <div className="settings-detail-grid">
              <DetailTile
                label="Tenant ID completo"
                value={currentUser.tenant_id || 'Non disponibile'}
                icon={<Building2 size={14} />}
                hint="Copia l’identificativo completo per supporto o audit."
                mono
                action={
                  currentUser.tenant_id ? (
                    <button
                      className="settings-icon-btn"
                      onClick={() => handleCopyId(currentUser.tenant_id!)}
                      title="Copia tenant ID"
                    >
                      {copiedId ? <Check size={14} /> : <Copy size={14} />}
                    </button>
                  ) : null
                }
              />
              <DetailTile
                label="Client"
                value={`${clientInfo.browser} su ${clientInfo.os}`}
                icon={<Monitor size={14} />}
                hint="Informazione ricavata dal browser attuale."
              />
              <DetailTile
                label="Ultimo accesso"
                value={formatDate(currentUser.last_login_at)}
                icon={<Users size={14} />}
                hint="Ultima sessione autenticata rilevata."
              />
              <DetailTile
                label="Build console"
                value={`v${pkg.version}`}
                icon={<HardDrive size={14} />}
                hint="Versione frontend attualmente in esecuzione."
                mono
              />
            </div>
          </SectionCard>

          <TeamAccessCard
            currentUser={currentUser}
            canManageTeam={canManageTeam}
            canInvite={canInvite}
            loading={loadingUsers}
            error={userError}
            inviteMsg={inviteMsg}
            inviting={inviting}
            maxUsers={maxUsers}
            teamCount={teamCount}
            teamMembers={teamMembers}
            showInvite={showInvite}
            inviteForm={inviteForm}
            onToggleInvite={() => setShowInvite((current) => !current)}
            onInviteSubmit={handleInvite}
            onInviteFormChange={setInviteForm}
            onToggleRole={handleToggleRole}
            onToggleActive={handleToggleActive}
          />
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;
