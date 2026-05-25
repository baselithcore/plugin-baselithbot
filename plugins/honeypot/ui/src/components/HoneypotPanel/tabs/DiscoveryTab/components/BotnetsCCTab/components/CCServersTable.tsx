import { Target } from 'lucide-react';
import type { HubNode } from '../../../../../../types/discovery';
import { getFlagEmoji } from '../../../utils';

interface CCServersTableProps {
  hubNodes: HubNode[];
  onHubClick: (hub: HubNode) => void;
}

export function CCServersTable({ hubNodes, onHubClick }: CCServersTableProps) {
  return (
    <table className="botnets-hub-table">
      <thead>
        <tr>
          <th>IP Address</th>
          <th>Threat Score</th>
          <th>Connected</th>
          <th>Centrality</th>
        </tr>
      </thead>
      <tbody>
        {hubNodes.slice(0, 15).map((hub) => (
          <tr
            key={hub.ip}
            className={hub.is_confirmed_cc ? 'hub-confirmed' : ''}
            onClick={() => onHubClick(hub)}
          >
            <td>
              <div className="hub-ip-cell">
                {hub.is_confirmed_cc && <Target size={12} className="hub-cc-icon" />}
                <code>{hub.ip}</code>
                {hub.country_code && (
                  <span className="hub-country">
                    {getFlagEmoji(hub.country_code)} {hub.country_code}
                  </span>
                )}
              </div>
            </td>
            <td>
              <div className="hub-threat-score">
                <div className="hub-threat-bar-container">
                  <div
                    className={`hub-threat-bar ${
                      hub.threat_score > 70 ? 'high' : hub.threat_score > 30 ? 'medium' : 'low'
                    }`}
                    style={{ width: `${Math.min(hub.threat_score, 100)}%` }}
                  />
                </div>
                <span className="hub-threat-value">{hub.threat_score.toFixed(0)}</span>
              </div>
            </td>
            <td>{hub.connected_bots}</td>
            <td>{hub.degree_centrality.toFixed(2)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
