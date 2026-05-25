import { Users, Server, Bug, Zap, AlertTriangle } from 'lucide-react';
import type { DiscoveryResult } from '../../../../types';

import './DiscoverySummary.css';

interface DiscoverySummaryProps {
  result: DiscoveryResult;
  zerodayCount: number;
  exploitCount: number;
}

export function DiscoverySummary({ result, zerodayCount, exploitCount }: DiscoverySummaryProps) {
  return (
    <div className="discovery-summary">
      <div className="discovery-stat stat-botnets">
        <div className="discovery-stat-icon-wrapper">
          <Users size={20} />
        </div>
        <div className="discovery-stat-content">
          <span className="discovery-stat-value">{result.summary.detected_botnets || 0}</span>
          <span className="discovery-stat-label">Botnets</span>
        </div>
      </div>

      <div className="discovery-stat stat-hubs">
        <div className="discovery-stat-icon-wrapper">
          <Server size={20} />
        </div>
        <div className="discovery-stat-content">
          <span className="discovery-stat-value">{result.summary.potential_cc_servers || 0}</span>
          <span className="discovery-stat-label">C&C Servers</span>
        </div>
      </div>

      <div className="discovery-stat stat-zerodays">
        <div className="discovery-stat-icon-wrapper">
          <Bug size={20} />
        </div>
        <div className="discovery-stat-content">
          <span className="discovery-stat-value">{zerodayCount}</span>
          <span className="discovery-stat-label">Zero-Days</span>
        </div>
      </div>

      <div className="discovery-stat stat-exploits">
        <div className="discovery-stat-icon-wrapper">
          <Zap size={20} />
        </div>
        <div className="discovery-stat-content">
          <span className="discovery-stat-value">{exploitCount}</span>
          <span className="discovery-stat-label">Exploits</span>
        </div>
      </div>

      <div className="discovery-stat stat-anomalies">
        <div className="discovery-stat-icon-wrapper">
          <AlertTriangle size={20} />
        </div>
        <div className="discovery-stat-content">
          <span className="discovery-stat-value">{result.summary.anomalies_detected || 0}</span>
          <span className="discovery-stat-label">Anomalies</span>
        </div>
      </div>
    </div>
  );
}
