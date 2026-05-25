import { ArrowUpRight, Sparkles } from 'lucide-react';
import { useMemo } from 'react';
import { JiraIssue } from '../../types';

type JiraSectionProps = {
  issues: JiraIssue[];
  expanded: boolean;
  onToggleExpanded: () => void;
  layout?: 'card' | 'panel';
};

const JiraSection = ({ issues, expanded, onToggleExpanded, layout = 'card' }: JiraSectionProps) => {
  const sortedIssues = useMemo(() => {
    const stories: JiraIssue[] = [];
    const others: JiraIssue[] = [];
    issues.forEach((issue) => {
      const t = String(issue.issue_type || '').toLowerCase();
      if (t.includes('story')) {
        stories.push(issue);
      } else {
        others.push(issue);
      }
    });
    return [...stories, ...others];
  }, [issues]);

  /* Reverting to original logic to support expand button */
  const visibleIssues = expanded ? sortedIssues : sortedIssues.slice(0, 3);

  const hiddenCount = Math.max(sortedIssues.length - visibleIssues.length, 0);
  const wrapperClass = layout === 'card' ? 'card secondary' : 'side-panel-section';

  return (
    <section className={wrapperClass}>
      <div className="section-header">
        <div>
          <p className="eyebrow">Ticket Jira collegati</p>
          <p className="muted small-text">
            {issues.length ? 'Issue collegate al contesto corrente.' : 'Nessuna issue disponibile.'}
          </p>
        </div>
        <span className="badge neutral">{issues.length}</span>
      </div>
      <div className="section-title">
        <Sparkles size={16} /> Jira
      </div>
      {issues.length === 0 && <div className="empty-card muted">Nessuna issue disponibile.</div>}
      {issues.length > 0 && (
        <div className="jira-list rich-list">
          {visibleIssues.map((issue, idx) => (
            <div key={issue.key || idx} className="jira-card rich">
              <div className="jira-card-top">
                <div className="jira-title-row">
                  <p className="jira-summary jira-summary-strong">
                    {issue.summary || 'Sommario non disponibile'}
                  </p>
                  {issue.issue_type && <span className="meta-pill subtle">{issue.issue_type}</span>}
                </div>
                <span className="meta-pill status">{issue.status || 'N/D'}</span>
              </div>
              <div className="jira-id">
                <span className="jira-key">{issue.key || '-'}</span>
              </div>
              {issue.url && (
                <div className="jira-card-foot">
                  <a href={issue.url} className="link-inline" target="_blank" rel="noreferrer">
                    Apri in Jira <ArrowUpRight size={14} />
                  </a>
                </div>
              )}
              {issue.error && <span className="inline-alert small-alert">{issue.error}</span>}
            </div>
          ))}
          {issues.length > 3 && (
            <button
              className="ghost small"
              onClick={onToggleExpanded}
              title={expanded ? 'Mostra meno' : `Mostra tutte le issue (${hiddenCount} nascoste)`}
            >
              {expanded ? 'Mostra meno' : `Mostra tutte (${hiddenCount})`}
            </button>
          )}
        </div>
      )}
    </section>
  );
};

export default JiraSection;
