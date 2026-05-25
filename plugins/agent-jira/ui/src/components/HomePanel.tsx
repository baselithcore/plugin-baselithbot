import {
  ArrowRight,
  FileText,
  MessageSquare,
  ShieldCheck,
  Sparkles,
  Search,
  Layers,
  Zap,
  Activity,
  Key,
} from 'lucide-react';
import React from 'react';

type HomePanelProps = {
  chatEnabled: boolean;
  analysisEnabled: boolean;
  jiraEnabled: boolean;
  jiraManual: boolean;
  apiKeyPresent: boolean;
  onSelectTab?: (tab: string) => void;
  onOpenJiraWizard?: () => void;
};

const HomePanel = ({
  chatEnabled,
  analysisEnabled,
  jiraEnabled,
  jiraManual,
  apiKeyPresent,
  onSelectTab,
  onOpenJiraWizard,
}: HomePanelProps) => {
  return (
    <div className="home-layout">
      <div className="home-main">
        {/* Hero Section */}
        <div className="home-hero-v2">
          <div className="badge-persistent" style={{ width: 'fit-content' }}>
            agent-jira · v1.19.1
          </div>
          <h2>Welcome to your AI Console</h2>
          <p className="lede-v2">
            Una piattaforma unificata e intelligente per accelerare il ciclo di sviluppo Agile.
            Analizza documenti, genera user storie sincronizzali nativamente con Jira in pochi clic.
          </p>
          <div style={{ marginTop: '12px' }}>
            <button className="pill-v2" onClick={() => onSelectTab?.('chat')}>
              Inizia una conversazione <ArrowRight size={16} />
            </button>
          </div>
        </div>

        {/* Feature Grid */}
        <div className="home-feature-grid">
          <div className="pm-tile-v2">
            <div className="tile-icon-v2" style={{ color: '#7ee0ff' }}>
              <MessageSquare size={28} />
            </div>
            <div>
              <h4>Conversazione AI</h4>
              <p>
                Interagisci con l'AI per esplorare il dominio del progetto, estrarre requisiti e
                consultare le fonti citate in tempo reale.
              </p>
            </div>
            <button className="pill link-pill" onClick={() => onSelectTab?.('chat')}>
              Vai alla Chat
            </button>
          </div>

          <div className="pm-tile-v2">
            <div className="tile-icon-v2" style={{ color: '#9333ea' }}>
              <Layers size={28} />
            </div>
            <div>
              <h4>Analisi Documentale</h4>
              <p>
                Carica PDF o documenti tecnici. L'AI genererà automaticamente User Story, criteri di
                accettazione BDD e Test Case.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button className="pill link-pill" onClick={() => onSelectTab?.('analysis')}>
                Analisi
              </button>
              <button className="pill link-pill" onClick={() => onSelectTab?.('kb')}>
                Knowledge Base
              </button>
            </div>
          </div>

          <div className="pm-tile-v2">
            <div className="tile-icon-v2" style={{ color: '#3cc9a6' }}>
              <ShieldCheck size={28} />
            </div>
            <div>
              <h4>Sincronizzazione Jira</h4>
              <p>
                Trasforma l'analisi in backlog operativo. Mappa le storie sui tuoi progetti Jira e
                mantieni tutto allineato.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button className="pill link-pill" onClick={() => onOpenJiraWizard?.()}>
                Configura Jira
              </button>
              <button className="pill link-pill" onClick={() => onSelectTab?.('analysis')}>
                Vai all'analisi
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Sidebar Dashboard */}
      <div className="home-sidebar-v2">
        <div className="sidebar-panel-v2">
          <span className="panel-title-v2">System Health</span>
          <div className="status-list-v2">
            <div className="status-row-v2">
              <span className="status-label-v2">API Connectivity</span>
              <span
                className={`status-chip ${apiKeyPresent ? 'ok' : 'off'} ${apiKeyPresent ? 'live' : ''}`}
              >
                <span className="dot" />
              </span>
            </div>
            <div className="status-row-v2">
              <span className="status-label-v2">Orchestrator Engine</span>
              <span
                className={`status-chip ${chatEnabled ? 'ok' : 'off'} ${chatEnabled ? 'live' : ''}`}
              >
                <span className="dot" />
              </span>
            </div>
            <div className="status-row-v2">
              <span className="status-label-v2">Analysis Pipeline</span>
              <span
                className={`status-chip ${analysisEnabled ? 'ok' : 'off'} ${analysisEnabled ? 'live' : ''}`}
              >
                <span className="dot" />
              </span>
            </div>
            <div className="status-row-v2">
              <span className="status-label-v2">Jira Integration</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {!jiraEnabled && (
                  <button
                    className="pill link-pill"
                    style={{ fontSize: 10, padding: '2px 8px' }}
                    onClick={() => onOpenJiraWizard?.()}
                  >
                    Setup
                  </button>
                )}
                <span
                  className={`status-chip ${jiraEnabled ? 'ok' : 'off'} ${jiraEnabled ? 'live' : ''}`}
                >
                  <span className="dot" />
                </span>
              </span>
            </div>
          </div>
        </div>

        <div className="sidebar-panel-v2">
          <span className="panel-title-v2">AI Insights Feed</span>
          <div className="insights-list-v2">
            <div className="insight-item-v2">
              <Sparkles size={18} className="insight-icon-v2" />
              <span className="insight-text-v2">
                Usa prompt chiari per ottenere risultati migliori nella generazione dei BDD.
              </span>
            </div>
            <div className="insight-item-v2">
              <Activity size={18} className="insight-icon-v2" />
              <span className="insight-text-v2">
                Le performance di analisi sono ottimali con documenti PDF testuali.
              </span>
            </div>
            <div className="insight-item-v2">
              <Zap size={18} className="insight-icon-v2" />
              <span className="insight-text-v2">
                Puoi velocizzare il flusso caricando più file nella Knowledge Base prima della chat.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePanel;
