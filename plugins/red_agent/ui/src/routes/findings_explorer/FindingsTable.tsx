import { useState } from 'react';
import { type Finding } from '../../lib/api';
import { Chip, FindingDetailModal, SeverityBadge } from '../../components/ui';

export function FindingsTable({ items }: { items: Finding[] }) {
  const [selected, setSelected] = useState<Finding | null>(null);
  return (
    <div className="overflow-x-auto">
      <table className="ra-table">
        <thead>
          <tr>
            <th className="w-24">Severity</th>
            <th>Issue</th>
            <th className="w-28">Scanner</th>
            <th className="w-28">CVE</th>
            <th className="w-20 text-right">CVSS</th>
            <th className="w-20 text-right">Risk</th>
            <th className="w-44">Target</th>
            <th className="w-32">Discovered</th>
          </tr>
        </thead>
        <tbody>
          {items.map((x) => (
            <tr
              key={x.id}
              onClick={() => setSelected(x)}
              className="cursor-pointer transition-colors hover:bg-bg-hover/50"
            >
              <td>
                <SeverityBadge severity={x.severity} full />
              </td>
              <td>
                <div className="min-w-0">
                  <div className="truncate font-medium text-text-primary">{x.title}</div>
                  {x.description && (
                    <div className="mt-0.5 truncate text-xs text-text-muted">{x.description}</div>
                  )}
                  {(x.controls ?? []).length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {x.controls.slice(0, 3).map((c) => (
                        <span
                          key={c}
                          className="rounded border border-status-success/30 bg-status-success/10 px-1.5 py-0.5 text-2xs font-mono text-status-success"
                        >
                          {c}
                        </span>
                      ))}
                      {x.controls.length > 3 && (
                        <span className="text-2xs font-mono text-text-muted">
                          +{x.controls.length - 3}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </td>
              <td>
                <Chip>{x.scanner}</Chip>
              </td>
              <td className="font-mono text-xs text-text-secondary">{x.cve ?? '—'}</td>
              <td className="text-right font-mono tabular-nums text-text-secondary">
                {x.cvss_score ?? '—'}
              </td>
              <td className="text-right font-mono tabular-nums text-text-secondary">
                {x.risk_score != null && Number.isFinite(x.risk_score)
                  ? x.risk_score.toFixed(1)
                  : '—'}
              </td>
              <td className="truncate font-mono text-xs text-text-secondary">
                {x.endpoint ?? x.target}
              </td>
              <td className="font-mono text-xs text-text-muted">
                {new Date(x.discovered_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <FindingDetailModal
        finding={selected}
        open={selected !== null}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}
