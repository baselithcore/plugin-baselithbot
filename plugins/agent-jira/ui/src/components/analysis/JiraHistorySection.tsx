import { ReactNode } from 'react';
import JiraResultsCard from '../JiraResultsCard';
import { JiraIssue } from '../../types';

type JiraHistorySectionProps = {
  title: string;
  subtitle: ReactNode;
  issues: JiraIssue[];
  status?: string;
};

const JiraHistorySection = ({
  title,
  subtitle,
  issues,
  status = 'Recuperate da Jira',
}: JiraHistorySectionProps) => {
  if (!issues.length) return null;
  return (
    <div className="card full">
      <div className="card-header">
        <div>
          <p className="eyebrow">Jira</p>
          <h3>{title}</h3>
          <p className="muted">{subtitle}</p>
        </div>
      </div>
      <JiraResultsCard status={status} results={issues} loading={false} />
    </div>
  );
};

export default JiraHistorySection;
