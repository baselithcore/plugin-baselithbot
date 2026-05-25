import { BookOpen, CircleHelp, Crosshair, ListChecks, ShieldAlert } from 'lucide-react';
import { JiraProject, ProjectPlanPayload, UserStoryPayload } from '../../types';
import StoryCard from './StoryCard';
import { sortStoriesByPriority } from './planUtils';

type PlanSectionsProps = {
  plan: ProjectPlanPayload;
  onSyncStory?: (story: UserStoryPayload) => void | Promise<void>;
  syncingStoryTitle?: string | null;
  globalSyncing?: boolean;
  onShowDetails?: (story: UserStoryPayload) => void;
  jiraProjects: JiraProject[];
  onSelectProject?: (story: UserStoryPayload, projectKey: string | null) => void;
  loadingProjects?: boolean;
  defaultProjectKey?: string | null;
};

const PlanSections = ({
  plan,
  onSyncStory,
  syncingStoryTitle,
  globalSyncing,
  onShowDetails,
  jiraProjects,
  onSelectProject,
  loadingProjects,
}: PlanSectionsProps) => (
  <>
    {plan.functional_summary && (
      <div className="analysis-step-card" style={{ background: 'var(--studio-card-bg)' }}>
        <div className="analysis-header-eyebrow">
          <BookOpen size={14} /> Sommario funzionale
        </div>
        <p style={{ margin: 0, fontSize: '15px', lineHeight: '1.7', color: 'var(--muted)' }}>
          {plan.functional_summary}
        </p>
      </div>
    )}

    {plan.key_requirements && plan.key_requirements.length > 0 && (
      <div className="analysis-step-card">
        <div className="analysis-header-eyebrow">
          <ListChecks size={14} /> Requisiti Chiave
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
            gap: '16px',
          }}
        >
          {plan.key_requirements.map((item, idx) => (
            <div key={idx} className="analysis-preflight-item ready">
              <div className="analysis-check-marker">RQ</div>
              <p style={{ margin: 0, fontSize: '14px', color: 'var(--studio-text)' }}>{item}</p>
            </div>
          ))}
        </div>
      </div>
    )}

    {plan.user_stories && plan.user_stories.length > 0 && (
      <div className="analysis-step-card">
        <div className="analysis-header-eyebrow">
          <Crosshair size={14} /> Backlog Operativo
        </div>
        <div className="story-grid">
          {sortStoriesByPriority(plan.user_stories).map((story) => (
            <StoryCard
              key={story.title}
              story={story}
              onSync={onSyncStory}
              syncing={syncingStoryTitle === story.title}
              disabled={globalSyncing}
              onShowDetails={onShowDetails}
              jiraProjects={jiraProjects}
              onSelectProject={onSelectProject}
              loadingProjects={loadingProjects}
            />
          ))}
        </div>
      </div>
    )}

    {plan.risks && plan.risks.length > 0 && (
      <div className="analysis-step-card" style={{ borderLeft: '4px solid #ff6b6b' }}>
        <div className="analysis-header-eyebrow" style={{ color: '#ff6b6b' }}>
          <ShieldAlert size={14} /> Analisi dei Rischi
        </div>
        <div style={{ display: 'grid', gap: '12px' }}>
          {plan.risks.map((risk, idx) => (
            <div key={idx} style={{ display: 'flex', gap: '12px', alignItems: 'start' }}>
              <span style={{ color: '#ff6b6b', fontSize: '18px' }}>•</span>
              <p style={{ margin: 0, fontSize: '14px', color: 'var(--muted)' }}>{risk}</p>
            </div>
          ))}
        </div>
      </div>
    )}

    {plan.open_questions && plan.open_questions.length > 0 && (
      <div className="analysis-step-card" style={{ borderLeft: '4px solid #ffd93d' }}>
        <div className="analysis-header-eyebrow" style={{ color: '#ffd93d' }}>
          <CircleHelp size={14} /> Domande Aperte
        </div>
        <div style={{ display: 'grid', gap: '12px' }}>
          {plan.open_questions.map((question, idx) => (
            <div key={idx} style={{ display: 'flex', gap: '12px', alignItems: 'start' }}>
              <span style={{ color: '#ffd93d', fontSize: '18px' }}>?</span>
              <p style={{ margin: 0, fontSize: '14px', color: 'var(--muted)' }}>{question}</p>
            </div>
          ))}
        </div>
      </div>
    )}
  </>
);

export default PlanSections;
