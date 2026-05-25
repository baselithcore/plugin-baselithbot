import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { ArrowUpRight, CheckCircle, Crosshair, Loader2 } from 'lucide-react';
import { JiraProject, ScenarioPayload, UserStoryPayload } from '../../types';
import { priorityTone, storyBusinessValue } from './planUtils';

type StoryDetailsModalProps = {
  story: UserStoryPayload | null;
  onClose: () => void;
  onSyncStory?: (story: UserStoryPayload) => void;
  onSyncScenarios?: (story: UserStoryPayload) => void;
  onSyncSingleScenario?: (story: UserStoryPayload, scenario: ScenarioPayload) => void;
  globalSyncing?: boolean;
  syncingStoryTitle?: string | null;
  syncingScenariosTitle?: string | null;
  jiraProjects?: JiraProject[];
  onSelectProject?: (story: UserStoryPayload, projectKey: string | null) => void;
  loadingProjects?: boolean;
};

const StoryDetailsModal = ({
  story,
  onClose,
  onSyncStory,
  onSyncScenarios,
  onSyncSingleScenario,
  globalSyncing,
  syncingStoryTitle,
  syncingScenariosTitle,
  jiraProjects,
  onSelectProject,
  loadingProjects,
}: StoryDetailsModalProps) => {
  const modalRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (story && modalRef.current) {
      modalRef.current.focus({ preventScroll: true });
    }
  }, [story]);

  if (!story || typeof document === 'undefined') return null;
  const hasProjectPicker = Boolean(onSelectProject && jiraProjects && jiraProjects.length > 0);
  const selectedProjectKey = story.jira_project_key || '';

  const renderBusinessValue = () => {
    const { businessValues } = storyBusinessValue(story);
    if (businessValues.length > 0) {
      return (
        <div className="muted">
          <strong>Business value:</strong>
          <ul className="bullet-list tight">
            {businessValues.map((val, idx) => (
              <li key={idx}>{val}</li>
            ))}
          </ul>
        </div>
      );
    }
    if (story.benefit) {
      return (
        <div className="muted">
          <strong>Business value:</strong>
          <ul className="bullet-list tight">
            <li>{story.benefit}</li>
          </ul>
        </div>
      );
    }
    return null;
  };

  const renderScenarios = () => {
    if (!story.scenarios?.length) return null;
    return (
      <div className="modal-section">
        <div className="section-title">
          <Crosshair size={14} /> Scenari BDD
        </div>
        <div className="scenario-grid full">
          {story.scenarios.map((scenario, idx) => {
            const givenSteps = scenario.given || [];
            const whenSteps = scenario.when || [];
            const thenSteps = scenario.then || [];
            const scenarioKey = scenario.scenario_id || scenario.title || `SCENARIO_${idx + 1}`;

            return (
              <div key={scenario.scenario_id || idx} className="scenario-card">
                <div className="scenario-head">
                  <div className="scenario-meta">
                    <span className="scenario-id">
                      {scenario.scenario_id || `SCENARIO_${idx + 1}`}
                    </span>
                    <span className="scenario-title">{scenario.title}</span>
                  </div>
                </div>

                <div className="scenario-body">
                  {givenSteps.length > 0 && (
                    <div className="bdd-column">
                      <span className="bdd-label given">Given</span>
                      <div className="bdd-steps">
                        {givenSteps.map((step, i) => (
                          <div key={`g-${i}`} className="bdd-step">
                            <span className="bdd-index">{i + 1}</span>
                            <span>{step}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {whenSteps.length > 0 && (
                    <div className="bdd-column">
                      <span className="bdd-label when">When</span>
                      <div className="bdd-steps">
                        {whenSteps.map((step, i) => (
                          <div key={`w-${i}`} className="bdd-step">
                            <span className="bdd-index">{i + 1}</span>
                            <span>{step}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {thenSteps.length > 0 && (
                    <div className="bdd-column">
                      <span className="bdd-label then">Then</span>
                      <div className="bdd-steps">
                        {thenSteps.map((step, i) => (
                          <div key={`t-${i}`} className="bdd-step">
                            <span className="bdd-index">{i + 1}</span>
                            <span>{step}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div className="scenario-actions">
                  <button
                    className="ghost tiny"
                    onClick={() => onSyncSingleScenario?.(story, scenario)}
                    disabled={
                      !onSyncSingleScenario ||
                      globalSyncing ||
                      syncingScenariosTitle === scenarioKey
                    }
                    title="Crea il singolo scenario in Jira"
                  >
                    {syncingScenariosTitle === scenarioKey ? (
                      <Loader2 className="spin" size={12} />
                    ) : (
                      <ArrowUpRight size={12} />
                    )}{' '}
                    Crea scenario in Jira
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderTestCases = () => {
    if (!story.test_cases?.length) return null;
    return (
      <div className="modal-section">
        <div className="section-title">
          <CheckCircle size={14} /> Test case
        </div>
        <div className="testcase-list">
          {story.test_cases.map((tc, idx) => (
            <div key={tc.title + idx} className="testcase-card">
              <div className="testcase-head">
                <strong>{tc.title}</strong>
                <span className="pill ghost">{tc.priority || 'Medium'}</span>
              </div>
              <p className="muted">{tc.objective}</p>
              <div className="step-stack">
                {tc.steps.map((step, i) => (
                  <span key={i} className="step-row">
                    <span className="step-tag">Step {i + 1}</span>
                    <span>{step}</span>
                  </span>
                ))}
              </div>
              <div className="muted">Esito atteso: {tc.expected_result}</div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return createPortal(
    <div
      className="modal-backdrop"
      onClick={onClose}
      style={{ backdropFilter: 'blur(80px)', background: 'rgba(0,0,0,0.6)' }}
    >
      <div
        className="analysis-card"
        style={{
          maxWidth: '960px',
          width: '90%',
          maxHeight: '92vh',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          padding: '36px',
          border: '1px solid var(--border)',
          boxShadow: 'var(--shadow)',
          position: 'relative',
        }}
        ref={modalRef}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          className="analysis-badge"
          onClick={onClose}
          style={{
            cursor: 'pointer',
            border: 'none',
            padding: '4px 10px',
            fontSize: '20px',
            position: 'absolute',
            top: '20px',
            right: '20px',
            zIndex: 10,
            background: 'var(--panel-strong)',
            color: 'var(--text)',
            borderRadius: '50%',
            width: '32px',
            height: '32px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            lineHeight: 1,
          }}
          title="Chiudi"
        >
          ×
        </button>

        <div className="analysis-step-header" style={{ marginBottom: '24px', flexShrink: 0 }}>
          <div className="analysis-step-info">
            <div className="analysis-header-eyebrow">Dettaglio Requisito</div>
            <h3
              style={{
                margin: '4px 0',
                fontSize: '26px',
                color: 'var(--text)',
                letterSpacing: '-0.02em',
                fontWeight: 800,
              }}
            >
              {story.title}
            </h3>
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            {story.priority && (
              <span
                className={`analysis-badge ${priorityTone(story.priority).includes('high') || priorityTone(story.priority).includes('critical') ? 'accent' : ''}`}
                style={{ fontSize: '12px', padding: '4px 12px' }}
              >
                Priorità {story.priority}
              </span>
            )}
          </div>
        </div>

        <div className="modal-body" style={{ overflowY: 'auto', paddingRight: '8px' }}>
          <div
            className="analysis-step-card"
            style={{
              background: 'var(--panel-strong)',
              marginBottom: '32px',
              padding: '28px',
              borderRadius: '18px',
              border: '1px solid var(--border)',
            }}
          >
            <p style={{ margin: 0, fontSize: '19px', lineHeight: '1.65', color: 'var(--text)' }}>
              <span style={{ opacity: 0.5, fontWeight: 500 }}>Come</span>{' '}
              <span style={{ fontWeight: 800 }}>{story.role.replace(/^(As |Role ?)/i, '')}</span>{' '}
              <span style={{ opacity: 0.5, fontWeight: 500 }}>desidero</span>{' '}
              <span style={{ fontWeight: 800 }}>{story.goal.replace(/^(I |Goal ?)/i, '')}</span>{' '}
              {story.benefit && (
                <>
                  <span style={{ opacity: 0.5, fontWeight: 500 }}>in modo da</span>{' '}
                  <span style={{ fontWeight: 800 }}>
                    {story.benefit.replace(/^(So |Outcome ?|Benefit ?)/i, '')}
                  </span>
                </>
              )}
              .
            </p>
          </div>

          {hasProjectPicker && (
            <div
              className="analysis-step-card"
              style={{
                marginBottom: '28px',
                padding: '20px',
                background: 'var(--panel)',
                border: '1px solid var(--border)',
              }}
            >
              <div
                className="analysis-header-eyebrow"
                style={{ fontSize: '10px', marginBottom: '8px' }}
              >
                Destinazione Jira
              </div>
              <select
                className="analysis-select"
                value={selectedProjectKey}
                onChange={(event) => onSelectProject?.(story, event.target.value || null)}
                disabled={globalSyncing || syncingStoryTitle === story.title || loadingProjects}
                style={{
                  width: '100%',
                  padding: '10px',
                  borderRadius: '8px',
                  background: 'var(--panel-strong)',
                  color: 'var(--text)',
                  border: '1px solid var(--border)',
                }}
              >
                <option value="">Seleziona un progetto Jira</option>
                {jiraProjects?.map((project) => (
                  <option key={project.key} value={project.key}>
                    {project.name} ({project.key})
                  </option>
                ))}
              </select>
            </div>
          )}

          {renderBusinessValue()}

          {story.labels && story.labels.length > 0 && (
            <div
              className="label-row"
              style={{ marginBottom: '32px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}
            >
              {story.labels.map((label) => (
                <span
                  key={label}
                  className="analysis-badge"
                  style={{ fontSize: '11px', background: 'var(--panel-strong)' }}
                >
                  {label}
                </span>
              ))}
            </div>
          )}

          {renderScenarios()}
          {renderTestCases()}
        </div>

        <div
          className="analysis-actions-bar"
          style={{
            marginTop: '24px',
            padding: '20px 0 0',
            borderTop: '1px solid var(--border)',
            flexShrink: 0,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ display: 'flex', gap: '12px' }}>
            {onSyncScenarios && story && (
              <button
                className="analysis-badge"
                style={{ cursor: 'pointer', padding: '8px 16px', borderRadius: '10px' }}
                onClick={() => onSyncScenarios(story)}
                disabled={!!syncingScenariosTitle || !selectedProjectKey}
              >
                {syncingScenariosTitle === story.title ? (
                  <Loader2 className="spin" size={14} />
                ) : (
                  <ArrowUpRight size={14} />
                )}
                Sync BDD
              </button>
            )}
          </div>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              className="analysis-badge"
              style={{ cursor: 'pointer', padding: '8px 16px', borderRadius: '10px' }}
              onClick={onClose}
            >
              Annulla
            </button>
            {onSyncStory && (
              <button
                className="analysis-primary-btn"
                style={{ padding: '8px 24px', borderRadius: '10px' }}
                onClick={() => onSyncStory(story)}
                disabled={syncingStoryTitle === story.title || !selectedProjectKey}
              >
                {syncingStoryTitle === story.title ? (
                  <Loader2 className="spin" size={14} />
                ) : (
                  <ArrowUpRight size={14} />
                )}
                Crea Story
              </button>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default StoryDetailsModal;
