import { useMemo, useState } from 'react';
import { BadgeCheck, ExternalLink, Loader2, TriangleAlert } from 'lucide-react';
import { JiraIssue } from '../types';

interface Props {
  status: string;
  results: JiraIssue[];
  loading?: boolean;
}

const JiraResultsCard = ({ status, results, loading }: Props) => {
  const [expanded, setExpanded] = useState(false);

  const sortedResults = useMemo(() => {
    const stories: JiraIssue[] = [];
    const others: JiraIssue[] = [];
    results.forEach((issue) => {
      const t = String(issue.issue_type || '').toLowerCase();
      if (t.includes('story')) {
        stories.push(issue);
      } else {
        others.push(issue);
      }
    });
    return [...stories, ...others];
  }, [results]);

  const colorForStatus = (value: string | undefined): string => {
    const val = (value || '').toLowerCase();
    if (val.includes('idea') || val.includes('backlog')) return 'status-idea';
    if (val.includes('todo') || val.includes('da fare')) return 'status-todo';
    if (val.includes('in progress') || val.includes('doing') || val.includes('wip'))
      return 'status-inprogress';
    if (val.includes('review') || val.includes('qa')) return 'status-review';
    if (val.includes('done') || val.includes('complet')) return 'status-done';
    if (val.includes('blocked') || val.includes('impediment')) return 'status-blocked';
    return 'status-neutral';
  };

  const formatStatus = (issue: JiraIssue): string => {
    const raw = (issue as any)?.status;

    const fields = (issue as any)?.fields;
    const candidates = [
      raw,
      (raw as any)?.name,
      (raw as any)?.text,
      (raw as any)?.status,
      (raw as any)?.displayName,
      (raw as any)?.statusCategory?.name,
      (raw as any)?.category?.name,
      (raw as any)?.state?.name,
      (raw as any)?.state,
      fields?.status?.name,
      fields?.status?.displayName,
      fields?.status?.statusCategory?.name,
      fields?.status?.category?.name,
      fields?.statusCategory?.name,
      fields?.statusCategory?.key,
      (issue as any)?.status_name,
      (issue as any)?.statusText,
      (issue as any)?.state_name,
      (issue as any)?.statusCategory?.name,
      (issue as any)?.status_category?.name,
    ];

    for (const value of candidates) {
      if (typeof value === 'string' && value.trim()) return value.trim();
      if (typeof value === 'number') return String(value);
    }
    return '—';
  };

  const visibleResults = expanded ? sortedResults : sortedResults.slice(0, 3);
  const canToggle = sortedResults.length > 3;

  return (
    <div className="jira-section">
      <div className="section-title">
        <BadgeCheck size={16} /> Jira
      </div>
      <p className="muted">{status}</p>
      {loading && (
        <div className="inline-alert">
          <Loader2 className="spin" size={16} /> Sincronizzazione in corso...
        </div>
      )}
      {results.length === 0 && !loading && <p className="muted">Nessuna issue creata.</p>}
      <div className="jira-grid">
        {visibleResults.map((issue, idx) => (
          <div key={issue.key || idx} className="jira-card">
            <div className="jira-head">
              <div className="jira-title-row">
                <p className="jira-summary jira-summary-strong">
                  {issue.summary || 'Sommario non disponibile'}
                </p>
                {issue.issue_type && <span className="jira-type-chip">{issue.issue_type}</span>}
              </div>
              <span className={`jira-status-chip ${colorForStatus(formatStatus(issue))}`}>
                {formatStatus(issue)}
              </span>
            </div>
            <div className="jira-head-left">
              <span className="jira-key">{issue.key || '-'}</span>
            </div>
            {issue.url && (
              <div className="jira-card-foot">
                <a href={issue.url} className="link-inline" target="_blank" rel="noreferrer">
                  Apri in Jira <ExternalLink size={14} />
                </a>
              </div>
            )}
            {issue.error && (
              <p className="inline-alert">
                <TriangleAlert size={14} /> {issue.error}
              </p>
            )}
          </div>
        ))}
      </div>
      {canToggle && (
        <div className="toggle-row">
          <button className="ghost small" onClick={() => setExpanded((v) => !v)}>
            {expanded
              ? 'Mostra meno'
              : `Mostra tutti (${results.length - visibleResults.length} in più)`}
          </button>
        </div>
      )}
    </div>
  );
};

export default JiraResultsCard;
