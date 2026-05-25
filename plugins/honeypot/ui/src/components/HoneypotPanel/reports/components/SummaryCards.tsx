import { SecurityReport } from '../../../types';

interface SummaryCardsProps {
  report: SecurityReport;
}

export function SummaryCards({ report }: SummaryCardsProps) {
  const formatNumber = (n: number) => n.toLocaleString();

  return (
    <div className="hp-preview-summary">
      <div className="hp-summary-card hp-summary-total">
        <div className="hp-summary-value">{formatNumber(report.threat_summary.total_events)}</div>
        <div className="hp-summary-label">Total Events</div>
      </div>
      <div className="hp-summary-card hp-summary-attackers">
        <div className="hp-summary-value">
          {formatNumber(report.threat_summary.unique_attackers)}
        </div>
        <div className="hp-summary-label">Unique Attackers</div>
      </div>
      <div className="hp-summary-card hp-summary-critical">
        <div className="hp-summary-value">{report.threat_summary.critical_events}</div>
        <div className="hp-summary-label">Critical Events</div>
      </div>
      <div className="hp-summary-card hp-summary-high">
        <div className="hp-summary-value">{report.threat_summary.high_events}</div>
        <div className="hp-summary-label">High Events</div>
      </div>
      <div className="hp-summary-card hp-summary-botnets">
        <div className="hp-summary-value">{report.threat_summary.detected_botnets}</div>
        <div className="hp-summary-label">Botnets</div>
      </div>
      <div className="hp-summary-card hp-summary-bot-traffic">
        <div className="hp-summary-value">
          {report.threat_summary.bot_traffic_percentage.toFixed(1)}%
        </div>
        <div className="hp-summary-label">Bot Traffic</div>
      </div>
    </div>
  );
}
