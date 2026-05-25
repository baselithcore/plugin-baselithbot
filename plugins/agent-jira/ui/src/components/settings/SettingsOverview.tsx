import { Link2, LogOut, Mail, Settings, ShieldCheck, Zap } from 'lucide-react';
import type { AuthUser } from '../../types';
import { MetricTile } from './SettingsPrimitives';

type Props = {
  currentUser: AuthUser;
  roleLabel: string;
  roleHelper: string;
  jiraReady: boolean;
  jiraProjects: number;
  jiraConfigurable: boolean;
  totalDependencies: number;
  readyDependencies: number;
  healthHealthy: boolean;
  canManageTeam: boolean;
  teamCount: number;
  maxUsers: number;
  onLogout: () => void;
  onOpenJiraWizard?: () => void;
};

const SettingsOverview = ({
  currentUser,
  roleLabel,
  roleHelper,
  jiraReady,
  jiraProjects,
  jiraConfigurable,
  totalDependencies,
  readyDependencies,
  healthHealthy,
  canManageTeam,
  teamCount,
  maxUsers,
  onLogout,
  onOpenJiraWizard,
}: Props) => (
  <>
    <div className="settings-topbar">
      <div>
        <p className="settings-eyebrow">Workspace settings</p>
        <h1 className="settings-page-title">Impostazioni account</h1>
        <p className="settings-page-subtitle">
          Una vista unica per profilo, integrazione Jira, salute sistema e gestione accessi.
        </p>
      </div>
      <div className="settings-topbar-actions">
        {jiraConfigurable && onOpenJiraWizard ? (
          <button className="settings-btn settings-btn--secondary" onClick={onOpenJiraWizard}>
            <Zap size={15} />
            Riconfigura Jira
          </button>
        ) : null}
        <button className="settings-btn settings-btn--danger" onClick={onLogout}>
          <LogOut size={15} />
          Esci
        </button>
      </div>
    </div>

    <section className="settings-hero">
      <div className="settings-hero-main">
        <span className="settings-hero-chip">
          <Settings size={14} />
          Dashboard account
        </span>
        <h2 className="settings-hero-title">
          {currentUser.display_name || currentUser.email.split('@')[0]}, il workspace è sotto
          controllo.
        </h2>
        <p className="settings-hero-description">
          Tutte le impostazioni operative sono organizzate in una sola pagina: stato profilo,
          connessione Jira, sessione locale e accessi del team.
        </p>
        <div className="settings-hero-tags">
          <span className="badge badge-soft">
            <ShieldCheck size={12} />
            {roleLabel}
          </span>
          <span className="badge badge-neutral">
            <Mail size={12} />
            {currentUser.email}
          </span>
          <span className={`badge ${jiraReady ? 'badge-soft' : 'badge-warn'}`}>
            <Link2 size={12} />
            {jiraReady ? 'Jira configurato' : 'Jira da completare'}
          </span>
        </div>
      </div>

      <div className="settings-metrics-grid">
        <MetricTile label="Profilo" value={roleLabel} helper={roleHelper} tone="success" />
        <MetricTile
          label="Jira"
          value={jiraReady ? 'Connesso' : 'Parziale'}
          helper={
            jiraProjects > 0
              ? `${jiraProjects} ${jiraProjects === 1 ? 'progetto attivo' : 'progetti attivi'}`
              : 'Nessun progetto predefinito'
          }
          tone={jiraReady ? 'success' : 'warning'}
        />
        <MetricTile
          label="Salute sistema"
          value={
            totalDependencies > 0 ? `${readyDependencies}/${totalDependencies}` : 'Check in corso'
          }
          helper={healthHealthy ? 'Tutte le dipendenze sono operative' : 'Verifica servizi'}
          tone={healthHealthy ? 'success' : 'warning'}
        />
        <MetricTile
          label="Accessi"
          value={canManageTeam ? `${teamCount}/${maxUsers}` : '1'}
          helper={canManageTeam ? 'Utenti nel workspace' : 'Modalità account singolo'}
        />
      </div>
    </section>
  </>
);

export default SettingsOverview;
