/**
 * DNSTable - Display DNS anomalies in a table
 */

import type { NetworkAnomaly } from '../../../../../../types/discovery';

interface DNSTableProps {
  anomalies: NetworkAnomaly[];
  onAnomalyClick: (anomaly: NetworkAnomaly) => void;
}

export function DNSTable({ anomalies, onAnomalyClick }: DNSTableProps) {
  const getTypeClass = (type: string): string => {
    if (type.includes('dga')) return 'dga';
    if (type.includes('tunnel')) return 'tunnel';
    if (type.includes('fastflux') || type.includes('flux')) return 'fastflux';
    return 'dns';
  };

  const getStatus = (anomaly: NetworkAnomaly): string => {
    const status = anomaly.metadata?.status;
    if (typeof status === 'string') return status;
    return anomaly.severity === 'critical' || anomaly.severity === 'high'
      ? 'blocked'
      : 'monitoring';
  };

  const getTypeLabel = (type: string): string => {
    return type.replace(/_/g, ' ').replace(/dga domain detection/i, 'DGA Detection');
  };

  return (
    <table className="dns-table">
      <thead>
        <tr>
          <th>Domain / Query</th>
          <th>Type</th>
          <th>Entropy</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {anomalies.map((a, i) => {
          const domain =
            a.metadata?.domain || a.metadata?.query_domain || a.involved_ips?.[0] || 'Unknown';
          const typeClass = getTypeClass(a.anomaly_type);
          const status = getStatus(a);
          const entropy = a.metadata?.entropy;

          return (
            <tr key={i} onClick={() => onAnomalyClick(a)} style={{ cursor: 'pointer' }}>
              <td>
                <span className="dns-domain" title={`Click for details\n${domain}`}>
                  {domain}
                </span>
              </td>
              <td>
                <span className={`dns-type-badge ${typeClass}`}>
                  {getTypeLabel(a.anomaly_type)}
                </span>
              </td>
              <td>
                {typeof entropy === 'number' && (
                  <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.8rem' }}>
                    {entropy.toFixed(2)}
                  </span>
                )}
              </td>
              <td>
                <span className={`dns-status ${status}`}>
                  <span className="dns-status-dot" />
                  {status}
                </span>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
