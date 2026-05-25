import { Target, Users, Shield, AlertTriangle } from 'lucide-react';
import KPICard from '../../common/KPICard';
import { getThreatLabel } from '../../../utils/analyticsHelpers';

interface TimeStats {
  lastHour: number;
  today: number;
  week: number;
}

interface KPIRowProps {
  totalEvents: number;
  uniqueIps: number;
  uniqueCountries: number;
  cveCorrelations: number;
  topMatchedCves: number;
  threatScore: number;
  timeStats: TimeStats;
}

export function KPIRow({
  totalEvents,
  uniqueIps,
  uniqueCountries,
  cveCorrelations,
  topMatchedCves,
  threatScore,
  timeStats,
}: KPIRowProps) {
  return (
    <div className="analytics-kpi-row">
      <KPICard
        icon={<Target size={24} />}
        label="Total Attacks"
        value={totalEvents}
        subValue={`${timeStats.lastHour} last hour`}
        trend={timeStats.lastHour > 0 ? 'up' : 'neutral'}
        accentColor="#ff4757"
      />
      <KPICard
        icon={<Users size={24} />}
        label="Unique IPs"
        value={uniqueIps}
        subValue={`${uniqueCountries} countries`}
        accentColor="#00d2d3"
      />
      <KPICard
        icon={<Shield size={24} />}
        label="CVE Correlations"
        value={cveCorrelations}
        subValue={`${topMatchedCves} unique CVEs`}
        accentColor="#a55eea"
      />
      <KPICard
        icon={<AlertTriangle size={24} />}
        label="Threat Score"
        value={threatScore}
        subValue={getThreatLabel(threatScore)}
        trend={threatScore >= 60 ? 'up' : threatScore >= 30 ? 'neutral' : 'down'}
        accentColor={threatScore >= 60 ? '#ff3366' : threatScore >= 30 ? '#ff9f43' : '#26de81'}
      />
    </div>
  );
}
