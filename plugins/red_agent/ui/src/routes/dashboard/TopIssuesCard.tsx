import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { Finding } from '../../lib/api';
import {
  Card,
  Chip,
  EmptyState,
  FindingDetailModal,
  Icon,
  SeverityBadge,
} from '../../components/ui';

export function TopIssuesCard({
  topFindings,
  totalFindings,
}: {
  topFindings: Finding[];
  totalFindings: number;
}) {
  const [selected, setSelected] = useState<Finding | null>(null);
  return (
    <Card
      className="lg:col-span-2"
      title="Top issues"
      subtitle={`${topFindings.length} of ${totalFindings} findings`}
      action={
        <Link to="/findings" className="ra-btn ra-btn-ghost ra-btn-sm">
          View all
          <Icon.ArrowRight size={12} />
        </Link>
      }
      padded={false}
    >
      {topFindings.length === 0 ? (
        <EmptyState
          compact
          icon={<Icon.ShieldCheck size={20} />}
          title="No findings yet"
          description="Run a scan to populate findings."
        />
      ) : (
        <table className="ra-table">
          <thead>
            <tr>
              <th>Issue</th>
              <th className="w-32">Scanner</th>
              <th className="w-32">CVE</th>
              <th className="w-20 text-right">CVSS</th>
              <th className="w-24">Severity</th>
            </tr>
          </thead>
          <tbody>
            {topFindings.map((x) => (
              <tr
                key={x.id}
                onClick={() => setSelected(x)}
                className="cursor-pointer transition-colors hover:bg-bg-hover/50"
              >
                <td>
                  <div className="min-w-0">
                    <div className="truncate font-medium text-text-primary">{x.title}</div>
                    <div className="mt-0.5 truncate font-mono text-xs text-text-muted">
                      {x.endpoint ?? x.target}
                    </div>
                  </div>
                </td>
                <td>
                  <Chip>{x.scanner}</Chip>
                </td>
                <td className="font-mono text-xs text-text-secondary">{x.cve ?? '—'}</td>
                <td className="text-right font-mono tabular-nums text-text-secondary">
                  {x.cvss_score ?? '—'}
                </td>
                <td>
                  <SeverityBadge severity={x.severity} full />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <FindingDetailModal
        finding={selected}
        open={selected !== null}
        onClose={() => setSelected(null)}
      />
    </Card>
  );
}
