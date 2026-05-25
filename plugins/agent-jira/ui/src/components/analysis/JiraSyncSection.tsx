import { ArrowUpRight, Loader2, Zap } from 'lucide-react';
import { AnalysisResponse, JiraIssue, JiraProject } from '../../types';
import JiraResultsCard from '../JiraResultsCard';

type JiraSyncSectionProps = {
  analysis: AnalysisResponse;
  createdIssues: JiraIssue[];
  syncing: boolean;
  syncingAllScenarios: boolean;
  scenarioSyncing: string | null;
  onSyncAllScenarios: () => void;
  onSyncJira: () => void;
  jiraProjects: JiraProject[];
  selectedProjectKey: string;
  onSelectProject?: (projectKey: string) => void;
  loadingProjects?: boolean;
  historicalIssues?: JiraIssue[];
  docId?: string | null;
};

const JiraSyncSection = ({
  analysis,
  createdIssues,
  syncing,
  syncingAllScenarios,
  scenarioSyncing,
  onSyncAllScenarios,
  onSyncJira,
  jiraProjects,
  selectedProjectKey,
  onSelectProject,
  loadingProjects,
  historicalIssues = [],
  docId,
}: JiraSyncSectionProps) => {
  const storyResults = createdIssues.filter((issue) =>
    String(issue.issue_type || '')
      .toLowerCase()
      .includes('story')
  ).length;
  const isBusy = syncing || syncingAllScenarios || !!scenarioSyncing;

  return (
    <>
      {/* ── Panel header ── */}
      <div className="ws-panel-header">
        <span className="ws-panel-label">Jira Sync</span>
        <span className={`ws-badge${analysis.jira.can_manual_sync ? ' ws-badge--accent' : ''}`}>
          <Zap size={9} />
          {analysis.jira.can_manual_sync ? 'Abilitato' : 'Solo lettura'}
        </span>
      </div>

      {/* ── Stats ── */}
      <div className="ws-inspector-section">
        <div className="ws-inspector-title">Riepilogo sincronizzazione</div>
        <div className="ws-metrics-grid">
          <div className="ws-metric-cell">
            <span className="ws-metric-label">Story create</span>
            <span className="ws-metric-value">{storyResults}</span>
          </div>
          <div className="ws-metric-cell">
            <span className="ws-metric-label">Progetto</span>
            <span
              className="ws-metric-value ws-metric-value--sm"
              style={{ color: selectedProjectKey ? 'var(--accent)' : 'var(--muted)' }}
            >
              {selectedProjectKey || '—'}
            </span>
          </div>
        </div>
      </div>

      {/* ── Sync controls ── */}
      {analysis.jira.can_manual_sync && (
        <div className="ws-inspector-section">
          <div className="ws-inspector-title">Controlli delivery</div>

          {/* Project selector */}
          <div className="ws-field" style={{ marginBottom: 10 }}>
            <label className="ws-field-label">Progetto Jira target</label>
            <select
              className="ws-select"
              value={selectedProjectKey}
              onChange={(e) => onSelectProject?.(e.target.value)}
              disabled={isBusy || loadingProjects}
            >
              <option value="">Seleziona progetto...</option>
              {jiraProjects.map((project) => (
                <option key={project.key} value={project.key}>
                  {project.name} ({project.key})
                </option>
              ))}
            </select>
          </div>

          {/* Action buttons */}
          <div className="ws-sync-controls">
            <button
              className="ws-sync-btn ws-sync-btn--primary"
              onClick={onSyncJira}
              disabled={syncing || !selectedProjectKey}
            >
              {syncing ? <Loader2 size={13} className="ws-spin" /> : <ArrowUpRight size={13} />}
              Sync User Stories
            </button>
            <button
              className="ws-sync-btn ws-sync-btn--secondary"
              onClick={onSyncAllScenarios}
              disabled={isBusy || !selectedProjectKey}
            >
              {syncingAllScenarios ? (
                <Loader2 size={13} className="ws-spin" />
              ) : (
                <ArrowUpRight size={13} />
              )}
              Sync tutti gli scenari
            </button>
          </div>
        </div>
      )}

      {/* ── Created issues ── */}
      {createdIssues.length > 0 && (
        <div className="ws-inspector-section">
          <div className="ws-inspector-title">Issue create</div>
          <div style={{ fontSize: 12 }}>
            <JiraResultsCard
              status={analysis.jira.status}
              results={createdIssues}
              loading={syncing}
            />
          </div>
        </div>
      )}

      {/* ── Historical issues ── */}
      {historicalIssues.length > 0 && (
        <div className="ws-inspector-section">
          <div className="ws-inspector-title">Storico Jira</div>
          <div style={{ fontSize: 12 }}>
            <p className="muted" style={{ marginBottom: 10 }}>
              Recuperato per {docId || "l'analisi corrente"}
            </p>
            <JiraResultsCard status="Archivio" results={historicalIssues} loading={false} />
          </div>
        </div>
      )}
    </>
  );
};

export default JiraSyncSection;
