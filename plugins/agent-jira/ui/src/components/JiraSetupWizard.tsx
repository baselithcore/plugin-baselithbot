import { useState, useCallback, useEffect } from 'react';
import {
  X,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Link2,
  Mail,
  Key,
  FolderKanban,
  Zap,
  ExternalLink,
  Shield,
  Check,
  Star,
} from 'lucide-react';
import {
  fetchJiraSettings,
  testJiraConnection,
  updateJiraSettings,
  previewJiraProjects,
} from '../api/client';
import type { JiraProject, JiraSettings } from '../types';

type Step = 'connect' | 'credentials' | 'project' | 'confirm';
const STEPS: Step[] = ['connect', 'credentials', 'project', 'confirm'];
const STEP_LABELS: Record<Step, string> = {
  connect: 'Connessione',
  credentials: 'Credenziali',
  project: 'Progetti',
  confirm: 'Conferma',
};

type Props = {
  open: boolean;
  onClose: () => void;
  onComplete?: () => void;
};

const JiraSetupWizard = ({ open, onClose, onComplete }: Props) => {
  const [step, setStep] = useState<Step>('connect');
  const [loading, setLoading] = useState(false);
  const [configurable, setConfigurable] = useState(false);

  // Form state
  const [baseUrl, setBaseUrl] = useState('');
  const [email, setEmail] = useState('');
  const [apiToken, setApiToken] = useState('');
  const [issueType, setIssueType] = useState('Story');
  const [testCaseIssueType, setTestCaseIssueType] = useState('Test Case');

  // Multi-project state
  const [availableProjects, setAvailableProjects] = useState<JiraProject[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [projectsError, setProjectsError] = useState('');
  const [defaultProjectKey, setDefaultProjectKey] = useState('');
  const [allowedProjectKeys, setAllowedProjectKeys] = useState<string[]>([]);
  const [manualProjectKey, setManualProjectKey] = useState('');

  // Test state
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'ok' | 'error'>('idle');
  const [testMessage, setTestMessage] = useState('');
  const [testUser, setTestUser] = useState('');

  // Save state
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'ok' | 'error'>('idle');
  const [saveMessage, setSaveMessage] = useState('');

  // Load existing settings on mount
  useEffect(() => {
    fetchJiraSettings()
      .then((res) => {
        setConfigurable(res.configurable);
        const s = res.settings;
        if (s.base_url) setBaseUrl(s.base_url);
        if (s.email) setEmail(s.email);
        if (s.default_project_key || s.project_key) {
          setDefaultProjectKey(s.default_project_key || s.project_key);
        }
        if (s.allowed_project_keys?.length) {
          setAllowedProjectKeys(s.allowed_project_keys);
        } else if (s.project_key) {
          setAllowedProjectKeys([s.project_key]);
        }
        if (s.issue_type) setIssueType(s.issue_type);
        if (s.test_case_issue_type) setTestCaseIssueType(s.test_case_issue_type);
      })
      .catch(() => {});
  }, []);

  // Fetch projects when entering step 3
  useEffect(() => {
    if (step !== 'project' || !baseUrl || !email || !apiToken) return;
    if (availableProjects.length > 0) return; // already fetched

    // Start fetch (loading state is managed via state initialization or trigger)
    previewJiraProjects({
      base_url: baseUrl.trim().replace(/\/$/, ''),
      email: email.trim(),
      api_token: apiToken.trim(),
    })
      .then((res) => {
        if (res.status === 'ok' && res.projects.length > 0) {
          setAvailableProjects(res.projects);
        } else {
          setProjectsError(res.message || 'Nessun progetto trovato.');
        }
      })
      .catch((err) => {
        setProjectsError(err.message || 'Errore nel caricamento dei progetti.');
      })
      .finally(() => setLoadingProjects(false));
  }, [step, baseUrl, email, apiToken, availableProjects.length]);

  const currentIdx = STEPS.indexOf(step);
  const canGoBack = currentIdx > 0;
  const isLastStep = step === 'confirm';

  const goNext = useCallback(() => {
    const nextStep = STEPS[currentIdx + 1];
    if (nextStep) {
      setStep(nextStep);
      // Trigger loading if entering project step
      if (nextStep === 'project' && availableProjects.length === 0) {
        setLoadingProjects(true);
        setProjectsError('');
      }
    }
  }, [currentIdx, availableProjects.length]);

  const goBack = useCallback(() => {
    const prev = STEPS[currentIdx - 1];
    if (prev) setStep(prev);
  }, [currentIdx]);

  const handleTest = useCallback(async () => {
    if (!baseUrl || !email || !apiToken) return;
    setTestStatus('testing');
    setTestMessage('');
    setTestUser('');
    try {
      const result = await testJiraConnection({
        base_url: baseUrl.trim().replace(/\/$/, ''),
        email: email.trim(),
        api_token: apiToken.trim(),
      });
      if (result.status === 'ok') {
        setTestStatus('ok');
        setTestMessage(result.message);
        setTestUser(result.user?.displayName || result.user?.emailAddress || '');
      } else {
        setTestStatus('error');
        setTestMessage(result.message);
      }
    } catch (err: any) {
      setTestStatus('error');
      setTestMessage(err.message || 'Errore durante il test.');
    }
  }, [baseUrl, email, apiToken]);

  const toggleProject = useCallback(
    (key: string) => {
      setAllowedProjectKeys((prev) => {
        if (prev.includes(key)) {
          // Don't allow removing the default
          if (key === defaultProjectKey) return prev;
          return prev.filter((k) => k !== key);
        }
        return [...prev, key];
      });
    },
    [defaultProjectKey]
  );

  const setAsDefault = useCallback((key: string) => {
    setDefaultProjectKey(key);
    setAllowedProjectKeys((prev) => (prev.includes(key) ? prev : [...prev, key]));
  }, []);

  const effectiveProjectKey =
    defaultProjectKey ||
    (allowedProjectKeys.length === 1 ? allowedProjectKeys[0] : '') ||
    manualProjectKey;

  const handleSave = useCallback(async () => {
    setSaveStatus('saving');
    setSaveMessage('');
    try {
      const dpk = effectiveProjectKey.trim().toUpperCase();
      const apk =
        allowedProjectKeys.length > 0 ? allowedProjectKeys.map((k) => k.toUpperCase()) : [dpk];

      const res = await updateJiraSettings({
        base_url: baseUrl.trim().replace(/\/$/, ''),
        email: email.trim(),
        api_token: apiToken.trim(),
        project_key: dpk,
        default_project_key: dpk,
        allowed_project_keys: apk,
        issue_type: issueType,
        test_case_issue_type: testCaseIssueType,
      });
      setSaveStatus('ok');
      setSaveMessage(res.message || 'Configurazione salvata.');
      setTimeout(() => {
        onComplete?.();
        onClose();
      }, 1200);
    } catch (err: any) {
      setSaveStatus('error');
      setSaveMessage(err.message || 'Errore durante il salvataggio.');
    }
  }, [
    baseUrl,
    email,
    apiToken,
    effectiveProjectKey,
    allowedProjectKeys,
    issueType,
    testCaseIssueType,
    onComplete,
    onClose,
  ]);

  if (!open) return null;

  const canAdvanceConnect = baseUrl.trim().length > 8;
  const canAdvanceCreds = email.trim().includes('@') && apiToken.trim().length > 5;
  const canAdvanceProject =
    availableProjects.length > 0
      ? allowedProjectKeys.length > 0 && !!defaultProjectKey
      : manualProjectKey.trim().length >= 2;

  const useDynamicPicker = availableProjects.length > 0;

  return (
    <div className="jw-overlay" onClick={onClose}>
      <div className="jw-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="jw-header">
          <div className="jw-header-left">
            <Zap size={18} />
            <span className="jw-header-title">Configurazione Jira</span>
          </div>
          <button className="jw-close" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        {/* Progress steps */}
        <div className="jw-progress">
          {STEPS.map((s, i) => (
            <div
              key={s}
              className={`jw-step ${s === step ? 'jw-step--active' : ''} ${
                i < currentIdx ? 'jw-step--done' : ''
              }`}
            >
              <div className="jw-step-dot">
                {i < currentIdx ? <CheckCircle2 size={14} /> : <span>{i + 1}</span>}
              </div>
              <span className="jw-step-label">{STEP_LABELS[s]}</span>
            </div>
          ))}
        </div>

        {/* Body */}
        <div className="jw-body">
          {/* Step 1: Connection URL */}
          {step === 'connect' && (
            <div className="jw-step-content">
              <div className="jw-step-icon">
                <Link2 size={32} />
              </div>
              <h3 className="jw-step-title">Connetti il tuo workspace Jira</h3>
              <p className="jw-step-desc">
                Inserisci l'URL del tuo Jira Cloud. Lo trovi nella barra degli indirizzi quando
                accedi a Jira.
              </p>
              <div className="jw-field">
                <label className="jw-field-label">URL Jira Cloud</label>
                <input
                  className="jw-input"
                  type="url"
                  placeholder="https://il-tuo-team.atlassian.net"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  autoFocus
                />
                <span className="jw-field-hint">Esempio: https://acme.atlassian.net</span>
              </div>
            </div>
          )}

          {/* Step 2: Credentials */}
          {step === 'credentials' && (
            <div className="jw-step-content">
              <div className="jw-step-icon">
                <Shield size={32} />
              </div>
              <h3 className="jw-step-title">Autenticazione API</h3>
              <p className="jw-step-desc">
                Usa un API token Atlassian per autenticarti in modo sicuro.{' '}
                <a
                  href="https://id.atlassian.com/manage-profile/security/api-tokens"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="jw-link"
                >
                  Crea un token <ExternalLink size={11} />
                </a>
              </p>
              <div className="jw-field">
                <label className="jw-field-label">
                  <Mail size={13} /> Email
                </label>
                <input
                  className="jw-input"
                  type="email"
                  placeholder="nome@azienda.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoFocus
                />
              </div>
              <div className="jw-field">
                <label className="jw-field-label">
                  <Key size={13} /> API Token
                </label>
                <input
                  className="jw-input"
                  type="password"
                  placeholder="Incolla il token Atlassian..."
                  value={apiToken}
                  onChange={(e) => setApiToken(e.target.value)}
                />
              </div>
              {/* Test connection button */}
              <button
                className={`jw-test-btn ${testStatus === 'ok' ? 'jw-test-btn--ok' : ''} ${testStatus === 'error' ? 'jw-test-btn--error' : ''}`}
                onClick={handleTest}
                disabled={!canAdvanceCreds || testStatus === 'testing'}
              >
                {testStatus === 'testing' && <Loader2 size={14} className="ws-spin" />}
                {testStatus === 'ok' && <CheckCircle2 size={14} />}
                {testStatus === 'error' && <AlertCircle size={14} />}
                {testStatus === 'idle' && <Zap size={14} />}
                {testStatus === 'testing'
                  ? 'Test in corso...'
                  : testStatus === 'ok'
                    ? 'Connesso'
                    : testStatus === 'error'
                      ? 'Riprova test'
                      : 'Testa connessione'}
              </button>
              {testMessage && (
                <div
                  className={`jw-test-result ${testStatus === 'ok' ? 'jw-test-result--ok' : 'jw-test-result--error'}`}
                >
                  {testStatus === 'ok' ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                  <div>
                    <span>{testMessage}</span>
                    {testUser && <span className="jw-test-user">Utente: {testUser}</span>}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 3: Project */}
          {step === 'project' && (
            <div className="jw-step-content">
              <div className="jw-step-icon">
                <FolderKanban size={32} />
              </div>
              <h3 className="jw-step-title">Progetti di destinazione</h3>
              <p className="jw-step-desc">
                Seleziona i progetti Jira abilitati e scegli quello predefinito. Potrai cambiare
                progetto per ogni user story prima della sincronizzazione.
              </p>

              {/* Dynamic project picker */}
              {loadingProjects && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                  <Loader2 size={16} className="ws-spin" />
                  <span style={{ fontSize: 12, color: 'var(--muted)' }}>
                    Caricamento progetti da Jira...
                  </span>
                </div>
              )}

              {useDynamicPicker && (
                <>
                  <div className="jw-projects-grid">
                    {availableProjects.map((p) => {
                      const isSelected = allowedProjectKeys.includes(p.key);
                      const isDefault = defaultProjectKey === p.key;
                      return (
                        <div
                          key={p.key}
                          className={`jw-project-card${isSelected ? ' jw-project-card--selected' : ''}${isDefault ? ' jw-project-card--default' : ''}`}
                          onClick={() => toggleProject(p.key)}
                        >
                          <div
                            className={`jw-project-check${isSelected ? ' jw-project-check--active' : ''}`}
                          >
                            {isSelected && <Check size={10} strokeWidth={3} />}
                          </div>
                          <div className="jw-project-info">
                            <div className="jw-project-key">{p.key}</div>
                            <div className="jw-project-name">{p.name}</div>
                          </div>
                          {isDefault && <span className="jw-project-badge">default</span>}
                          {isSelected && !isDefault && (
                            <button
                              className="jw-project-badge"
                              style={{
                                cursor: 'pointer',
                                background: 'transparent',
                                border: '1px solid var(--border)',
                                color: 'var(--muted)',
                              }}
                              title="Imposta come predefinito"
                              onClick={(e) => {
                                e.stopPropagation();
                                setAsDefault(p.key);
                              }}
                            >
                              <Star size={8} />
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                  <p className="jw-projects-hint">
                    Clicca per selezionare/deselezionare. Clicca{' '}
                    <Star size={8} style={{ verticalAlign: 'middle' }} /> per impostare il
                    predefinito.
                  </p>
                </>
              )}

              {/* Fallback: manual input when projects can't be fetched */}
              {!loadingProjects && !useDynamicPicker && (
                <div className="jw-field">
                  <label className="jw-field-label">Chiave progetto</label>
                  <input
                    className="jw-input"
                    type="text"
                    placeholder="PROJ"
                    value={manualProjectKey}
                    onChange={(e) => {
                      const val = e.target.value.toUpperCase();
                      setManualProjectKey(val);
                      setDefaultProjectKey(val);
                      setAllowedProjectKeys(val ? [val] : []);
                    }}
                    autoFocus
                    style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
                  />
                  <span className="jw-field-hint">
                    La trovi nell'URL del progetto, es. /projects/<strong>PROJ</strong>/board
                  </span>
                  {projectsError && (
                    <div className="jw-test-result jw-test-result--error" style={{ marginTop: 8 }}>
                      <AlertCircle size={12} />
                      <span>{projectsError} — inserisci la chiave manualmente.</span>
                    </div>
                  )}
                </div>
              )}

              <div className="jw-fields-row" style={{ marginTop: 14 }}>
                <div className="jw-field">
                  <label className="jw-field-label">Tipo issue Story</label>
                  <select
                    className="jw-select"
                    value={issueType}
                    onChange={(e) => setIssueType(e.target.value)}
                  >
                    <option value="Story">Story</option>
                    <option value="Task">Task</option>
                    <option value="Bug">Bug</option>
                  </select>
                </div>
                <div className="jw-field">
                  <label className="jw-field-label">Tipo issue Test Case</label>
                  <select
                    className="jw-select"
                    value={testCaseIssueType}
                    onChange={(e) => setTestCaseIssueType(e.target.value)}
                  >
                    <option value="Test Case">Test Case</option>
                    <option value="Bug">Bug</option>
                    <option value="Sub-task">Sub-task</option>
                    <option value="Task">Task</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Confirm */}
          {step === 'confirm' && (
            <div className="jw-step-content">
              <div className="jw-step-icon jw-step-icon--accent">
                <CheckCircle2 size={32} />
              </div>
              <h3 className="jw-step-title">Riepilogo configurazione</h3>
              <p className="jw-step-desc">
                Verifica i dati e salva. Potrai modificarli in qualsiasi momento.
              </p>
              <div className="jw-summary">
                <div className="jw-summary-row">
                  <span className="jw-summary-key">URL</span>
                  <span className="jw-summary-val">{baseUrl}</span>
                </div>
                <div className="jw-summary-row">
                  <span className="jw-summary-key">Email</span>
                  <span className="jw-summary-val">{email}</span>
                </div>
                <div className="jw-summary-row">
                  <span className="jw-summary-key">Token</span>
                  <span className="jw-summary-val">{'*'.repeat(12)}</span>
                </div>
                <div className="jw-summary-row">
                  <span className="jw-summary-key">Progetto predefinito</span>
                  <span className="jw-summary-val jw-summary-val--accent">
                    {defaultProjectKey || manualProjectKey || '—'}
                  </span>
                </div>
                {allowedProjectKeys.length > 1 && (
                  <div className="jw-summary-row">
                    <span className="jw-summary-key">Progetti abilitati</span>
                    <span className="jw-summary-val">{allowedProjectKeys.join(', ')}</span>
                  </div>
                )}
                <div className="jw-summary-row">
                  <span className="jw-summary-key">Issue type</span>
                  <span className="jw-summary-val">
                    {issueType} / {testCaseIssueType}
                  </span>
                </div>
              </div>
              {!configurable && (
                <div className="jw-test-result jw-test-result--error" style={{ marginTop: 12 }}>
                  <AlertCircle size={14} />
                  <span>
                    Multi-tenancy non attiva. Le impostazioni verranno applicate solo via variabili
                    d'ambiente.
                  </span>
                </div>
              )}
              {saveMessage && (
                <div
                  className={`jw-test-result ${saveStatus === 'ok' ? 'jw-test-result--ok' : 'jw-test-result--error'}`}
                  style={{ marginTop: 12 }}
                >
                  {saveStatus === 'ok' ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                  <span>{saveMessage}</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer with navigation */}
        <div className="jw-footer">
          <div className="jw-footer-left">
            {canGoBack && (
              <button className="jw-nav-btn jw-nav-btn--back" onClick={goBack}>
                <ArrowLeft size={14} />
                Indietro
              </button>
            )}
          </div>
          <div className="jw-footer-right">
            {!isLastStep && (
              <button
                className="jw-nav-btn jw-nav-btn--next"
                onClick={goNext}
                disabled={
                  (step === 'connect' && !canAdvanceConnect) ||
                  (step === 'credentials' && !canAdvanceCreds) ||
                  (step === 'project' && !canAdvanceProject)
                }
              >
                Avanti
                <ArrowRight size={14} />
              </button>
            )}
            {isLastStep && configurable && (
              <button
                className="jw-nav-btn jw-nav-btn--save"
                onClick={handleSave}
                disabled={saveStatus === 'saving' || saveStatus === 'ok'}
              >
                {saveStatus === 'saving' ? (
                  <Loader2 size={14} className="ws-spin" />
                ) : saveStatus === 'ok' ? (
                  <CheckCircle2 size={14} />
                ) : (
                  <Zap size={14} />
                )}
                {saveStatus === 'saving'
                  ? 'Salvataggio...'
                  : saveStatus === 'ok'
                    ? 'Salvato!'
                    : 'Salva configurazione'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default JiraSetupWizard;
