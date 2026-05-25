import { FileDown, LayoutList, Loader2 } from 'lucide-react';
import PlanCard from '../PlanCard';
import { AnalysisResponse, JiraProject, ScenarioPayload, UserStoryPayload } from '../../types';

type PlanSectionProps = {
  analysis: AnalysisResponse;
  storySyncing: string | null;
  scenarioSyncing: string | null;
  globalSyncing: boolean;
  downloadingReport: boolean;
  onDownloadReport: () => void;
  onSyncStory?: (story: UserStoryPayload) => void;
  onSyncScenarios?: (story: UserStoryPayload) => void;
  onSyncSingleScenario?: (story: UserStoryPayload, scenario: ScenarioPayload) => void;
  jiraProjects: JiraProject[];
  loadingJiraProjects: boolean;
  onSelectStoryProject?: (story: UserStoryPayload, projectKey: string | null) => void;
};

const PlanSection = ({
  analysis,
  storySyncing,
  scenarioSyncing,
  globalSyncing,
  downloadingReport,
  onDownloadReport,
  onSyncStory,
  onSyncScenarios,
  onSyncSingleScenario,
  jiraProjects,
  loadingJiraProjects,
  onSelectStoryProject,
}: PlanSectionProps) => {
  const storyCount = analysis.plan?.user_stories?.length ?? 0;
  const riskCount = analysis.plan?.risks?.length ?? 0;
  const scenarioCount =
    analysis.plan?.user_stories?.reduce(
      (total, story) => total + (story.scenarios?.length ?? 0),
      0
    ) ?? 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      {/* Canvas toolbar */}
      <div className="ws-canvas-toolbar">
        <div className="ws-canvas-toolbar-left">
          <LayoutList size={15} style={{ color: 'var(--accent)', flexShrink: 0 }} />
          <span className="ws-canvas-title">Backlog generato</span>
          <span className="ws-badge">{storyCount} stories</span>
          {scenarioCount > 0 && <span className="ws-badge">{scenarioCount} scenari</span>}
          {riskCount > 0 && <span className="ws-badge">{riskCount} rischi</span>}
        </div>
        <button className="ws-btn" onClick={onDownloadReport} disabled={downloadingReport}>
          {downloadingReport ? <Loader2 size={12} className="ws-spin" /> : <FileDown size={12} />}
          Export PDF
        </button>
      </div>

      {/* Scrollable content */}
      <div className="ws-canvas-content">
        <PlanCard
          plan={analysis.plan}
          onSyncStory={analysis.jira.can_manual_sync ? onSyncStory : undefined}
          syncingStoryTitle={storySyncing}
          globalSyncing={globalSyncing}
          onSyncScenarios={analysis.jira.can_manual_sync ? onSyncScenarios : undefined}
          syncingScenariosTitle={scenarioSyncing}
          onSyncSingleScenario={analysis.jira.can_manual_sync ? onSyncSingleScenario : undefined}
          jiraProjects={jiraProjects}
          loadingJiraProjects={loadingJiraProjects}
          onSelectStoryProject={onSelectStoryProject}
        />
      </div>
    </div>
  );
};

export default PlanSection;
