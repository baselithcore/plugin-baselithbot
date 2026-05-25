import { ArrowUpRight, Loader2, BookOpenText } from 'lucide-react';
import { JiraProject, UserStoryPayload } from '../../types';
import { storyBusinessValue } from './planUtils';

type StoryCardProps = {
  story: UserStoryPayload;
  onSync?: (story: UserStoryPayload) => void | Promise<void>;
  syncing?: boolean;
  disabled?: boolean;
  onShowDetails?: (story: UserStoryPayload) => void;
  jiraProjects?: JiraProject[];
  onSelectProject?: (story: UserStoryPayload, projectKey: string | null) => void;
  loadingProjects?: boolean;
};

/* Priority config — returns label + left-border accent color */
const priorityConfig = (value?: string): { label: string; color: string; bg: string } => {
  const v = (value || '').toLowerCase();
  if (v === 'highest' || v === 'blocker' || v === 'critical')
    return { label: 'Critical', color: '#ff3b30', bg: 'rgba(255,59,48,0.08)' };
  if (v.includes('high')) return { label: 'High', color: '#ff9500', bg: 'rgba(255,149,0,0.08)' };
  if (v.includes('medium'))
    return { label: 'Medium', color: '#f2c94c', bg: 'rgba(242,201,76,0.1)' };
  if (v.includes('low')) return { label: 'Low', color: '#34c759', bg: 'rgba(52,199,89,0.08)' };
  return { label: value || '—', color: 'var(--muted)', bg: 'transparent' };
};

const StoryCard = ({
  story,
  onSync,
  syncing,
  disabled,
  onShowDetails,
  jiraProjects,
  onSelectProject,
  loadingProjects,
}: StoryCardProps) => {
  const scenariosCount = story.scenarios?.length || 0;
  const testsCount = story.test_cases?.length || 0;
  const acceptanceCount = story.acceptance?.length || 0;
  const hasDetails = scenariosCount > 0 || testsCount > 0 || acceptanceCount > 0;

  const contextLabel =
    story.labels?.find((label) => {
      const lowered = label.toLowerCase();
      return (
        /-[0-9a-f]{6}$/i.test(lowered) || lowered === 'knowledge-base' || lowered === 'analysis'
      );
    }) || null;

  const priority = priorityConfig(story.priority);
  const hasProjectPicker = Boolean(onSelectProject && jiraProjects && jiraProjects.length > 0);
  const selectedProjectKey = story.jira_project_key || '';

  return (
    <div className="sc-card">
      {/* Priority stripe */}
      <div
        className="sc-stripe"
        style={{ background: priority.color }}
        title={`Priorità: ${priority.label}`}
      />

      <div className="sc-body">
        {/* Header */}
        <div className="sc-header">
          <div className="sc-header-left">
            <span
              className="sc-priority"
              style={{ color: priority.color, background: priority.bg }}
            >
              {priority.label}
            </span>
            {contextLabel && <span className="sc-label">{contextLabel}</span>}
          </div>
          <span className="sc-type">User Story</span>
        </div>

        {/* Title */}
        <h4 className="sc-title">{story.title}</h4>

        {/* Story sentence — natural language, fluent format */}
        <p className="sc-story-text">
          <span className="sc-story-label">Come</span>
          <em>{story.role.replace(/^(As |Role ?)/i, '')}</em>
          <span className="sc-story-label">, desidero</span>
          <em>{story.goal.replace(/^(I |Goal ?)/i, '')}</em>
          {story.benefit ? (
            <>
              <span className="sc-story-label">, in modo da</span>
              <em>{story.benefit.replace(/^(So |Outcome ?|Benefit ?)/i, '')}</em>
            </>
          ) : null}
          .
        </p>

        {/* Meta badges */}
        {hasDetails && (
          <div className="sc-meta">
            {scenariosCount > 0 && (
              <span className="sc-meta-chip">
                <span className="sc-meta-dot" style={{ background: '#7ee0ff' }} />
                {scenariosCount} Scenari BDD
              </span>
            )}
            {testsCount > 0 && (
              <span className="sc-meta-chip">
                <span className="sc-meta-dot" style={{ background: '#34c759' }} />
                {testsCount} Test case
              </span>
            )}
            {acceptanceCount > 0 && (
              <span className="sc-meta-chip">
                <span className="sc-meta-dot" style={{ background: '#ff9500' }} />
                {acceptanceCount} Criteri
              </span>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="sc-footer">
          <div className="sc-footer-left">
            {hasDetails && onShowDetails && (
              <button className="sc-link-btn" onClick={() => onShowDetails(story)}>
                <BookOpenText size={12} />
                Dettagli
              </button>
            )}
          </div>

          {onSync && (
            <div className="sc-footer-right">
              {hasProjectPicker && (
                <select
                  className="sc-project-select"
                  value={selectedProjectKey}
                  onChange={(e) => onSelectProject?.(story, e.target.value || null)}
                  disabled={disabled || syncing || loadingProjects}
                >
                  <option value="">Progetto…</option>
                  {jiraProjects?.map((p) => (
                    <option key={p.key} value={p.key}>
                      {p.key}
                    </option>
                  ))}
                </select>
              )}
              <button
                className="sc-sync-btn"
                onClick={() => onSync(story)}
                disabled={disabled || syncing || !selectedProjectKey}
                title={
                  !selectedProjectKey
                    ? 'Seleziona un progetto prima di sincronizzare'
                    : 'Crea su Jira'
                }
              >
                {syncing ? <Loader2 size={12} className="spin" /> : <ArrowUpRight size={12} />}
                Sync
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StoryCard;
