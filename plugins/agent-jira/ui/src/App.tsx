import { Suspense, lazy, useCallback, useEffect, useMemo, useState } from 'react';
import { Tag } from 'lucide-react';
import Hero from './components/Hero';
import Tabs from './components/Tabs';
import HomePanel from './components/HomePanel';
import LoginPage from './components/LoginPage';
import SuperuserWizard from './components/SuperuserWizard';
import JiraSetupWizard from './components/JiraSetupWizard';
import SettingsPanel from './components/SettingsPanel';
import { useAuth } from './hooks/useAuth';
import { API_KEY_PRESENT } from './api/client';
import pkg from '../package.json';
import { fetchConfig } from './api/client';
import { ConsoleConfig } from './types';

const loadChatPanel = () => import('./components/ChatPanel');
const loadAnalysisPanel = () => import('./components/AnalysisPanel');
const loadKbPanel = () => import('./components/KbPanel');

const ChatPanel = lazy(loadChatPanel);
const AnalysisPanel = lazy(loadAnalysisPanel);
const KbPanel = lazy(loadKbPanel);

type TabId = 'home' | 'chat' | 'analysis' | 'kb' | 'settings';

const App = () => {
  const {
    user,
    maxUsers,
    loading: authLoading,
    error: authError,
    login,
    register,
    logout,
    isAuthenticated,
  } = useAuth();
  const [config, setConfig] = useState<ConsoleConfig | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('home');
  const [error, setError] = useState<string | null>(null);
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    if (typeof window === 'undefined') return 'light';
    const stored = localStorage.getItem('console-theme');
    return stored === 'dark' ? 'dark' : 'light';
  });
  const [preselectedKb, setPreselectedKb] = useState<{ path: string; timestamp: number } | null>(
    null
  );
  const [jiraWizardOpen, setJiraWizardOpen] = useState(false);
  // First-boot superuser gate. SuperuserWizard interroga
  // /auth/bootstrap/status e chiama onComplete (che setta false) sia se
  // needs_bootstrap=false sia dopo creazione admin riuscita.
  const [bootstrapPending, setBootstrapPending] = useState(true);
  // AUTH_REQUIRED è letto dal config; se il backend non richiede auth, skip login
  const authRequired = config?.auth_required ?? false;

  const handleJiraWizardComplete = useCallback(() => {
    fetchConfig()
      .then(setConfig)
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchConfig()
      .then((cfg) => {
        setConfig(cfg);
        // Auto-switch to analysis if chat is disabled but analysis is on
        if (!cfg.chat_enabled && cfg.analysis_enabled) {
          setActiveTab('analysis');
        }
      })
      .catch((err) => setError(err.message));
  }, [isAuthenticated]);

  // Precarica i chunk dei tab principali dopo il primo render per ridurre la latenza al cambio tab.
  useEffect(() => {
    const id = window.setTimeout(() => {
      loadChatPanel();
      loadAnalysisPanel();
      loadKbPanel();
    }, 300);
    return () => window.clearTimeout(id);
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('console-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const tabs = useMemo(() => {
    return [
      {
        id: 'home' as const,
        label: 'Home',
        disabled: false,
      },
      {
        id: 'chat' as const,
        label: 'Conversazione',
        disabled: config ? !config.chat_enabled : false,
      },
      {
        id: 'analysis' as const,
        label: 'Analisi documenti',
        disabled: config ? !config.analysis_enabled : false,
      },
      {
        id: 'kb' as const,
        label: 'Knowledge Base',
        disabled: false,
      },
    ];
  }, [config]);

  const handleOpenKbDoc = (path: string) => {
    setPreselectedKb({ path, timestamp: Date.now() });
    setActiveTab('analysis');
  };

  const versionLabel = pkg.version ? `Versione ${pkg.version}` : null;

  // First-boot gate: se Postgres ha 0 utenti, mostra il SuperuserWizard
  // PRIMA della LoginPage. Self-checking via /auth/bootstrap/status —
  // se already-bootstrapped chiama subito onComplete e si auto-smonta.
  // Stesso pattern usato da wikigen / dbview / docheck.
  if (authRequired && !isAuthenticated && bootstrapPending) {
    return <SuperuserWizard onComplete={() => setBootstrapPending(false)} />;
  }

  // Show login page if auth is required and user is not authenticated
  if (authRequired && !isAuthenticated && !authLoading) {
    return (
      <LoginPage onLogin={login} onRegister={register} error={authError} loading={authLoading} />
    );
  }

  // Show loading while checking auth
  if (authRequired && authLoading) {
    return (
      <div
        className="page"
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      >
        <div className="card card-muted">Verifica autenticazione...</div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="glow glow-1" />
      <div className="glow glow-2" />
      <div className={`shell ${activeTab === 'chat' ? 'chat-mode' : ''}`}>
        <Hero
          jiraManual={config?.jira_manual_required ?? false}
          analysisEnabled={config?.analysis_enabled ?? false}
          error={error}
          theme={theme}
          onToggleTheme={toggleTheme}
          user={isAuthenticated ? user : null}
          onLogout={isAuthenticated ? logout : undefined}
          onOpenSettings={isAuthenticated ? () => setActiveTab('settings') : undefined}
        >
          <Tabs tabs={tabs} active={activeTab} onChange={setActiveTab} />
        </Hero>

        <div className="panel-stack">
          <div className={activeTab === 'home' ? 'panel' : 'panel panel-hidden'}>
            <HomePanel
              chatEnabled={config?.chat_enabled ?? false}
              analysisEnabled={config?.analysis_enabled ?? false}
              jiraEnabled={config?.jira_enabled ?? false}
              jiraManual={config?.jira_manual_required ?? false}
              apiKeyPresent={API_KEY_PRESENT || isAuthenticated}
              onSelectTab={(tab) => setActiveTab(tab as TabId)}
              onOpenJiraWizard={() => setJiraWizardOpen(true)}
            />
          </div>
          <div className={activeTab === 'chat' ? 'panel' : 'panel panel-hidden'}>
            <Suspense fallback={<div className="card card-muted">Caricamento...</div>}>
              <ChatPanel />
            </Suspense>
          </div>
          <div className={activeTab === 'kb' ? 'panel' : 'panel panel-hidden'}>
            <Suspense fallback={<div className="card card-muted">Caricamento...</div>}>
              <KbPanel onOpenInAnalysis={handleOpenKbDoc} tabActive={activeTab === 'kb'} />
            </Suspense>
          </div>
          <div className={activeTab === 'analysis' ? 'panel' : 'panel panel-hidden'}>
            {config?.analysis_enabled ? (
              <Suspense fallback={<div className="card card-muted">Caricamento...</div>}>
                <AnalysisPanel initialKb={preselectedKb || undefined} />
              </Suspense>
            ) : (
              config && (
                <div className="card card-muted">
                  L'analisi documentale è disabilitata in configurazione.
                </div>
              )
            )}
          </div>
          {isAuthenticated && user && (
            <div className={activeTab === 'settings' ? 'panel' : 'panel panel-hidden'}>
              <SettingsPanel
                currentUser={user}
                maxUsers={maxUsers}
                onLogout={logout}
                onOpenJiraWizard={() => setJiraWizardOpen(true)}
              />
            </div>
          )}
        </div>

        <JiraSetupWizard
          key={jiraWizardOpen ? 'open' : 'closed'}
          open={jiraWizardOpen}
          onClose={() => setJiraWizardOpen(false)}
          onComplete={handleJiraWizardComplete}
        />

        <footer className="footer">
          <div className="footer-content">
            <span className="copyright">© 2025 Giovanni Ippolito</span>
            {pkg.version && (
              <>
                <span className="footer-sep">/</span>
                <span className="version-tag">v{pkg.version}</span>
              </>
            )}
          </div>
        </footer>
      </div>
    </div>
  );
};

export default App;
