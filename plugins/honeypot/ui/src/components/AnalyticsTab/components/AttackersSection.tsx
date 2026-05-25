import { Globe } from 'lucide-react';
import { normalizeIpDisplay } from '../../api';
import { getCountryFlag } from '../../geoUtils';

interface TopAttacker {
  ip: string;
  country_code?: string;
  count: number;
}

interface AttackersSectionProps {
  topAttackerIps: TopAttacker[];
}

export function AttackersSection({ topAttackerIps }: AttackersSectionProps) {
  const maxCount = topAttackerIps?.[0]?.count || 1;

  return (
    <div className="analytics-section-card">
      <h3 className="analytics-section-title">
        <Globe size={18} /> Top Attackers
      </h3>
      <div className="analytics-attackers-list">
        {topAttackerIps?.slice(0, 5).map((attacker, idx) => {
          const percentage = (attacker.count / maxCount) * 100;
          return (
            <div key={attacker.ip} className="analytics-attacker-item">
              <span className="analytics-attacker-rank">#{idx + 1}</span>
              <span className="analytics-attacker-flag">
                {getCountryFlag(attacker.country_code)}
              </span>
              <span className="analytics-attacker-ip">{normalizeIpDisplay(attacker.ip)}</span>
              <div className="analytics-attacker-bar-wrapper">
                <div className="analytics-attacker-bar" style={{ width: `${percentage}%` }} />
              </div>
              <span className="analytics-attacker-count">{attacker.count}</span>
            </div>
          );
        })}
        {(!topAttackerIps || topAttackerIps.length === 0) && (
          <div className="analytics-empty">No attackers yet</div>
        )}
      </div>
    </div>
  );
}
