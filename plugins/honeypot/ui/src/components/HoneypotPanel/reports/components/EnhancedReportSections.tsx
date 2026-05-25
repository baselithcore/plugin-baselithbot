/**
 * Enhanced Report Sections with Professional Visualizations
 * Modern charts and interactive components
 */

import { FileText, Globe, Bug, TrendingUp, Shield, AlertTriangle, Activity } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { SecurityReport } from '../../../types';
import {
  AttackTimelineChart,
  GeoDistributionChart,
  AttackCategoriesChart,
  SeverityDistributionChart,
  AnimatedMetric,
} from '../visualizations';

// Executive Summary with Enhanced Styling
export function EnhancedExecutiveSummary({ content }: { content: string }) {
  if (!content) return null;

  return (
    <div className="hp-preview-section-enhanced">
      <h3>
        <FileText size={20} />
        Research Summary
      </h3>
      <div className="hp-executive-summary-content">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </div>
  );
}

// Threat Overview with Animated Metrics
export function ThreatOverviewMetrics({ report }: { report: SecurityReport }) {
  const { threat_summary } = report;

  return (
    <div className="hp-preview-section-enhanced">
      <h3>
        <Shield size={20} />
        Data Collection Overview
      </h3>
      <div className="hp-metrics-grid">
        <AnimatedMetric
          value={threat_summary.total_events}
          label="Total Events"
          icon={<Activity size={24} />}
          color="#00f5ff"
        />
        <AnimatedMetric
          value={threat_summary.unique_attackers}
          label="Unique Attackers"
          icon={<AlertTriangle size={24} />}
          color="#9d4edd"
        />
        <AnimatedMetric
          value={threat_summary.critical_events}
          label="Critical Events"
          icon={<Bug size={24} />}
          color="#ff4757"
        />
        <AnimatedMetric
          value={threat_summary.bot_traffic_percentage}
          label="Bot Traffic"
          suffix="%"
          decimals={1}
          icon={<TrendingUp size={24} />}
          color="#ffa502"
        />
      </div>
    </div>
  );
}

// Attack Analytics with Timeline and Categories
export function EnhancedAttackAnalytics({ report }: { report: SecurityReport }) {
  const hasTimeline = report.attack_timeline && report.attack_timeline.length > 0;
  const hasCategories =
    report.threat_summary.top_attack_categories &&
    Object.keys(report.threat_summary.top_attack_categories).length > 0;

  if (!hasTimeline && !hasCategories) return null;

  return (
    <div className="hp-preview-section-enhanced">
      <h3>
        <Activity size={20} />
        Attack Pattern Analysis
      </h3>

      {/* Severity Distribution */}
      <div style={{ marginBottom: '32px' }}>
        <h4 style={{ color: 'rgba(255,255,255,0.8)', marginBottom: '16px', fontSize: '14px' }}>
          Severity Distribution
        </h4>
        <SeverityDistributionChart summary={report.threat_summary} />
      </div>

      {/* Attack Timeline */}
      {hasTimeline && (
        <div style={{ marginBottom: '32px' }}>
          <h4 style={{ color: 'rgba(255,255,255,0.8)', marginBottom: '16px', fontSize: '14px' }}>
            Attack Timeline
          </h4>
          <AttackTimelineChart timeline={report.attack_timeline} />
        </div>
      )}

      {/* Attack Categories */}
      {hasCategories && (
        <div>
          <h4 style={{ color: 'rgba(255,255,255,0.8)', marginBottom: '16px', fontSize: '14px' }}>
            Attack Categories
          </h4>
          <AttackCategoriesChart categories={report.threat_summary.top_attack_categories} />
        </div>
      )}
    </div>
  );
}

// Geographic Distribution with Chart
export function EnhancedGeoDistribution({ data }: { data: SecurityReport['geo_distribution'] }) {
  if (!data?.length) return null;

  return (
    <div className="hp-preview-section-enhanced">
      <h3>
        <Globe size={20} />
        Geographic Distribution
      </h3>

      {/* Chart */}
      <div style={{ marginBottom: '24px' }}>
        <GeoDistributionChart data={data} />
      </div>

      {/* Table for detailed info */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid rgba(157, 78, 221, 0.3)' }}>
              <th
                style={{ padding: '12px 8px', textAlign: 'left', color: 'rgba(255,255,255,0.8)' }}
              >
                Country
              </th>
              <th
                style={{ padding: '12px 8px', textAlign: 'right', color: 'rgba(255,255,255,0.8)' }}
              >
                Attacks
              </th>
              <th
                style={{ padding: '12px 8px', textAlign: 'right', color: 'rgba(255,255,255,0.8)' }}
              >
                Unique IPs
              </th>
              <th
                style={{ padding: '12px 8px', textAlign: 'left', color: 'rgba(255,255,255,0.8)' }}
              >
                Primary Types
              </th>
            </tr>
          </thead>
          <tbody>
            {data.slice(0, 10).map((geo, idx) => (
              <tr
                key={geo.country_code}
                style={{
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                  background: idx % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent',
                }}
              >
                <td style={{ padding: '10px 8px', color: '#fff' }}>
                  <span style={{ fontWeight: 500 }}>
                    {geo.country_name} ({geo.country_code})
                  </span>
                </td>
                <td style={{ padding: '10px 8px', textAlign: 'right', color: '#ff4757' }}>
                  {geo.attack_count.toLocaleString()}
                </td>
                <td style={{ padding: '10px 8px', textAlign: 'right', color: '#00f5ff' }}>
                  {geo.unique_ips}
                </td>
                <td
                  style={{ padding: '10px 8px', color: 'rgba(255,255,255,0.6)', fontSize: '12px' }}
                >
                  {geo.primary_attack_types?.slice(0, 2).join(', ') || '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Export all sections
export * from './ReportSections'; // Re-export original sections
