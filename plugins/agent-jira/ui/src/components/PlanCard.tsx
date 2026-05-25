import React, { useState } from 'react';
import { JiraProject, ProjectPlanPayload, ScenarioPayload, UserStoryPayload } from '../types';
import PlanSections from './plan/PlanSections';
import StoryDetailsModal from './plan/StoryDetailsModal';

interface Props {
  plan?: ProjectPlanPayload | null;
  onSyncStory?: (story: UserStoryPayload) => void | Promise<void>;
  syncingStoryTitle?: string | null;
  globalSyncing?: boolean;
  onSyncScenarios?: (story: UserStoryPayload) => void | Promise<void>;
  syncingScenariosTitle?: string | null;
  onSyncSingleScenario?: (
    story: UserStoryPayload,
    scenario: ScenarioPayload
  ) => void | Promise<void>;
  jiraProjects: JiraProject[];
  loadingJiraProjects?: boolean;
  onSelectStoryProject?: (story: UserStoryPayload, projectKey: string | null) => void;
}

const PlanCard = ({
  plan,
  onSyncStory,
  syncingStoryTitle,
  globalSyncing,
  onSyncScenarios,
  syncingScenariosTitle,
  onSyncSingleScenario,
  jiraProjects,
  loadingJiraProjects,
  onSelectStoryProject,
}: Props) => {
  const [expandedStory, setExpandedStory] = useState<UserStoryPayload | null>(null);

  const handleSelectProject = (story: UserStoryPayload, projectKey: string | null) => {
    onSelectStoryProject?.(story, projectKey);
    setExpandedStory((current) =>
      current && current.title === story.title
        ? { ...current, jira_project_key: projectKey }
        : current
    );
  };

  if (!plan) {
    return <div className="muted">Nessun project plan disponibile.</div>;
  }

  return (
    <div className="plan-card">
      <PlanSections
        plan={plan}
        onSyncStory={onSyncStory}
        syncingStoryTitle={syncingStoryTitle}
        globalSyncing={globalSyncing}
        onShowDetails={setExpandedStory}
        jiraProjects={jiraProjects}
        onSelectProject={handleSelectProject}
        loadingProjects={loadingJiraProjects}
      />

      <StoryDetailsModal
        story={expandedStory}
        onClose={() => setExpandedStory(null)}
        onSyncStory={onSyncStory}
        onSyncScenarios={onSyncScenarios}
        onSyncSingleScenario={onSyncSingleScenario}
        globalSyncing={globalSyncing}
        syncingStoryTitle={syncingStoryTitle}
        syncingScenariosTitle={syncingScenariosTitle}
        jiraProjects={jiraProjects}
        onSelectProject={handleSelectProject}
        loadingProjects={loadingJiraProjects}
      />
    </div>
  );
};

export default PlanCard;
