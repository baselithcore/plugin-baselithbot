import React from 'react';
import {
  BookOpenText,
  CircleHelp,
  FolderSearch,
  LoaderCircle,
  RefreshCw,
  ScanText,
  Workflow,
} from 'lucide-react';
import AnalysisForm from './analysis/AnalysisForm';
import DocumentDetails from './analysis/DocumentDetails';
import JiraSyncSection from './analysis/JiraSyncSection';
import JiraHistorySection from './analysis/JiraHistorySection';
import PlanSection from './analysis/PlanSection';
import { useAnalysisPanel } from './analysis/useAnalysisPanel';

type AnalysisPanelProps = {
  initialKb?: { path: string; timestamp: number };
};

const AnalysisPanel = ({ initialKb }: AnalysisPanelProps) => {
  const {
    prompt,
    setPrompt,
    selectedKb,
    setSelectedKb,
    file,
    kbDocuments,
    analysis,
    onFileChange,
    onAnalyze,
    loading,
    disableAnalyze,
    error,
    toast,
    storing,
    onStore,
    syncing,
    syncingAllScenarios,
    scenarioSyncing,
    onSyncAllScenarios,
    onSyncJira,
    docId,
    baselineIssues,
    historicalIssues,
    createdIssues,
    storySyncing,
    onSyncSingleStory,
    onSyncScenarios,
    onSyncSingleScenario,
    downloadingReport,
    onDownloadReport,
    jiraProjects,
    loadingJiraProjects,
    onSelectStoryProject,
    selectedProjectKey,
    onSelectBulkProject,
    onResetSession,
    analysisStartTime,
  } = useAnalysisPanel(initialKb);

  const analysisReady = !!analysis;
  const storyCount = analysis?.plan?.user_stories?.length ?? 0;
  const requirementCount = analysis?.plan?.key_requirements?.length ?? 0;
  const riskCount = analysis?.plan?.risks?.length ?? 0;

  const activeSource = selectedKb
    ? (kbDocuments.find((d) => d.path === selectedKb)?.label ?? selectedKb)
    : (file?.name ?? null);

  const statusMode = loading ? 'analyzing' : analysisReady ? 'done' : 'idle';

  return (
    <div className="ws-shell">
      {/* ── Toolbar ── */}
      <header className="ws-toolbar">
        <div className="ws-toolbar-left">
          <ScanText size={15} style={{ color: 'var(--accent)', flexShrink: 0 }} />
          <span className="ws-toolbar-title">Analysis Studio</span>

          {activeSource && (
            <>
              <span className="ws-breadcrumb-arrow">›</span>
              <span className="ws-breadcrumb-seg">{activeSource}</span>
            </>
          )}

          {docId && (
            <>
              <span className="ws-breadcrumb-arrow">›</span>
              <span className="ws-breadcrumb-seg" style={{ color: 'var(--accent)' }}>
                {docId}
              </span>
            </>
          )}

          {analysisReady && (
            <span className="ws-badge ws-badge--success ws-badge--dot" style={{ marginLeft: 4 }}>
              Completato
            </span>
          )}

          {loading && (
            <span className="ws-badge ws-badge--accent" style={{ marginLeft: 4 }}>
              <LoaderCircle size={10} className="ws-spin" />
              Analisi…
            </span>
          )}
        </div>

        <div className="ws-toolbar-right">
          {kbDocuments.length > 0 && (
            <span className="ws-badge">
              <BookOpenText size={10} />
              {kbDocuments.length} doc KB
            </span>
          )}
          {analysisReady && (
            <button className="ws-btn" onClick={onResetSession}>
              <RefreshCw size={12} />
              Nuova sessione
            </button>
          )}
        </div>
      </header>

      {/* ── Body (3-column grid) ── */}
      <div className="ws-body">
        {/* LEFT — Configuration */}
        <aside className="ws-panel ws-panel--left">
          <AnalysisForm
            prompt={prompt}
            onPromptChange={setPrompt}
            selectedKb={selectedKb}
            onKbChange={setSelectedKb}
            file={file}
            kbDocuments={kbDocuments}
            onFileChange={onFileChange}
            onAnalyze={onAnalyze}
            loading={loading}
            disableAnalyze={disableAnalyze}
            error={error}
            toast={toast}
            onResetSession={onResetSession}
            hasAnalysis={analysisReady}
            duration={analysis?.duration}
            analysisStartTime={analysisStartTime}
          />
        </aside>

        {/* MAIN — Canvas / output */}
        <main
          className="ws-panel ws-panel--main"
          style={{ display: 'flex', flexDirection: 'column' }}
        >
          {analysis ? (
            <>
              <PlanSection
                analysis={analysis}
                storySyncing={storySyncing}
                scenarioSyncing={scenarioSyncing}
                globalSyncing={syncing || syncingAllScenarios}
                downloadingReport={downloadingReport}
                onDownloadReport={onDownloadReport}
                onSyncStory={onSyncSingleStory}
                onSyncScenarios={onSyncScenarios}
                onSyncSingleScenario={onSyncSingleScenario}
                jiraProjects={jiraProjects}
                loadingJiraProjects={loadingJiraProjects}
                onSelectStoryProject={onSelectStoryProject}
              />
            </>
          ) : (
            <div className="ws-empty">
              <div className="ws-empty-icon">
                <ScanText size={24} />
              </div>
              <h3 className="ws-empty-title">Studio pronto</h3>
              <p className="ws-empty-desc">
                Configura la sorgente e avvia il planner per generare backlog, BDD e test case.
              </p>

              <div className="ws-empty-steps">
                <div className="ws-empty-step">
                  <span className="ws-empty-step-num">01</span>
                  <span className="ws-empty-step-text">
                    Carica un file o seleziona un documento dalla Knowledge Base
                  </span>
                </div>
                <div className="ws-empty-step">
                  <span className="ws-empty-step-num">02</span>
                  <span className="ws-empty-step-text">
                    Aggiungi un brief opzionale per orientare il planner
                  </span>
                </div>
                <div className="ws-empty-step">
                  <span className="ws-empty-step-num">03</span>
                  <span className="ws-empty-step-text">
                    Avvia l'analisi e rivedi il backlog generato, poi sincronizza su Jira
                  </span>
                </div>
              </div>
            </div>
          )}
        </main>

        {/* RIGHT — Inspector */}
        <aside className="ws-panel ws-panel--right">
          <div className="ws-panel-scroll">
            {analysis ? (
              <>
                <DocumentDetails
                  analysis={analysis}
                  storing={storing}
                  onStore={onStore}
                  onResetSession={onResetSession}
                />
                <JiraSyncSection
                  analysis={analysis}
                  createdIssues={createdIssues}
                  syncing={syncing}
                  syncingAllScenarios={syncingAllScenarios}
                  scenarioSyncing={scenarioSyncing}
                  onSyncAllScenarios={onSyncAllScenarios}
                  onSyncJira={onSyncJira}
                  jiraProjects={jiraProjects}
                  selectedProjectKey={selectedProjectKey}
                  onSelectProject={onSelectBulkProject}
                  loadingProjects={loadingJiraProjects}
                  historicalIssues={[...baselineIssues, ...historicalIssues]}
                  docId={docId || undefined}
                />
              </>
            ) : (
              <div className="ws-inspector-section">
                <div className="ws-inspector-title">Guida workspace</div>
                <div className="ws-guide-card">
                  <div className="ws-guide-item">
                    <span className="ws-guide-bullet" />
                    <span className="ws-guide-text">
                      Scegli upload locale o documento KB come sorgente unica
                    </span>
                  </div>
                  <div className="ws-guide-item">
                    <span className="ws-guide-bullet" />
                    <span className="ws-guide-text">
                      Il planner genera user story, scenari BDD e test case
                    </span>
                  </div>
                  <div className="ws-guide-item">
                    <span className="ws-guide-bullet" />
                    <span className="ws-guide-text">
                      Review e sync Jira restano nello stesso canvas
                    </span>
                  </div>
                  <div className="ws-guide-item">
                    <span className="ws-guide-bullet" />
                    <span className="ws-guide-text">
                      {kbDocuments.length > 0
                        ? `${kbDocuments.length} documenti KB disponibili per il riuso`
                        : 'Nessun documento KB ancora indicizzato'}
                    </span>
                  </div>
                </div>

                <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div className="ws-prop-row">
                    <span className="ws-prop-key">
                      <FolderSearch size={10} /> Documenti KB
                    </span>
                    <span className="ws-prop-val">{kbDocuments.length}</span>
                  </div>
                  <div className="ws-prop-row">
                    <span className="ws-prop-key">
                      <Workflow size={10} /> Modalità
                    </span>
                    <span className="ws-prop-val ws-prop-val--accent">Attesa</span>
                  </div>
                  <div className="ws-prop-row">
                    <span className="ws-prop-key">
                      <CircleHelp size={10} /> Sorgente
                    </span>
                    <span className="ws-prop-val">{selectedKb ? 'KB' : file ? 'Upload' : '—'}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </aside>
      </div>

      {/* ── Status bar ── */}
      <footer className="ws-statusbar">
        <div className="ws-statusbar-left">
          <span className="ws-status-item">
            <span
              className={`ws-status-dot${statusMode === 'analyzing' ? ' ws-status-dot--pulse' : ''}`}
            />
            {statusMode === 'analyzing'
              ? 'Analisi in corso'
              : statusMode === 'done'
                ? 'Analisi completata'
                : 'Studio in attesa'}
          </span>
          {analysisReady && (
            <>
              <span className="ws-status-item">{storyCount} stories</span>
              <span className="ws-status-item">{requirementCount} requisiti</span>
              <span className="ws-status-item">{riskCount} rischi</span>
            </>
          )}
        </div>
        <div className="ws-statusbar-right">
          {docId && <span className="ws-status-item">{docId}</span>}
          <span className="ws-status-item">Analysis Studio</span>
        </div>
      </footer>
    </div>
  );
};

export default AnalysisPanel;
