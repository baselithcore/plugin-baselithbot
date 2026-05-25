/**
 * ActivityItem - Display a single activity event
 */

import { ExternalLink } from 'lucide-react';
import type { NetworkAnomaly } from '../../../../../../types/discovery';

interface ActivityItemProps {
  event: NetworkAnomaly;
}

export function ActivityItem({ event }: ActivityItemProps) {
  const time = event.detected_at
    ? new Date(event.detected_at).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      })
    : '--:--';

  const sourceIp = event.involved_ips?.[0] || 'Unknown';

  return (
    <div className="activity-item">
      <span className="activity-time">{time}</span>
      <span className="activity-type">{event.anomaly_type.replace(/_/g, ' ')}</span>
      <span className="activity-ip">{sourceIp}</span>
      {sourceIp !== 'Unknown' && (
        <a
          href={`https://www.abuseipdb.com/check/${sourceIp}`}
          target="_blank"
          rel="noopener noreferrer"
          className="activity-link"
          title="Check on AbuseIPDB"
        >
          <ExternalLink size={14} />
        </a>
      )}
    </div>
  );
}
