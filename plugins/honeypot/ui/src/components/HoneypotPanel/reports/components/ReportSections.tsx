import { FileText, Globe, Bug, Target, List, CheckCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { SecurityReport } from '../../../types';

// Helper for severity colors
const getSeverityColor = (severity: string) => {
  switch (severity.toLowerCase()) {
    case 'critical':
      return 'var(--hp-danger)';
    case 'high':
      return '#ff6b35';
    case 'medium':
      return 'var(--hp-warning)';
    case 'low':
      return 'var(--hp-info)';
    default:
      return 'var(--hp-text-muted)';
  }
};

const formatNumber = (n: number) => n.toLocaleString();

export function ExecutiveSummary({ content }: { content: string }) {
  if (!content) return null;

  return (
    <div className="hp-preview-section">
      <h3>
        <FileText size={16} />
        Executive Summary
      </h3>
      <div className="hp-executive-summary-content">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </div>
  );
}

export function GeoDistribution({ data }: { data: SecurityReport['geo_distribution'] }) {
  if (!data?.length) return null;

  return (
    <div className="hp-preview-section">
      <h3>
        <Globe size={16} />
        Geographic Distribution
      </h3>
      <div className="hp-geo-table">
        <table>
          <thead>
            <tr>
              <th>Country</th>
              <th>Attacks</th>
              <th>Unique IPs</th>
            </tr>
          </thead>
          <tbody>
            {data.slice(0, 10).map((geo) => (
              <tr key={geo.country_code}>
                <td>
                  <span className="hp-country-name">
                    {geo.country_name} ({geo.country_code})
                  </span>
                </td>
                <td>{formatNumber(geo.attack_count)}</td>
                <td>{geo.unique_ips}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function BotnetActivity({ data }: { data: SecurityReport['botnet_activity'] }) {
  if (!data?.length) return null;

  return (
    <div className="hp-preview-section">
      <h3>
        <Bug size={16} />
        Detected Botnet Activity
      </h3>
      <div className="hp-botnet-list">
        {data.map((botnet) => (
          <div key={botnet.cluster_id} className="hp-botnet-card">
            <div className="hp-botnet-header">
              <span className="hp-botnet-id">{botnet.cluster_id}</span>
              <span
                className="hp-botnet-severity"
                style={{ color: getSeverityColor(botnet.severity) }}
              >
                {botnet.severity.toUpperCase()}
              </span>
            </div>
            <div className="hp-botnet-stats">
              <div>
                <strong>{botnet.member_count}</strong> members
              </div>
              <div>
                Score: <strong>{botnet.attack_coordination_score.toFixed(2)}</strong>
              </div>
            </div>
            {botnet.suspected_cc_servers.length > 0 && (
              <div className="hp-botnet-cc">C&C: {botnet.suspected_cc_servers.join(', ')}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export function Vulnerabilities({ data }: { data: SecurityReport['vulnerabilities'] }) {
  if (!data?.length) return null;

  return (
    <div className="hp-preview-section">
      <h3>
        <Target size={16} />
        Discovered Vulnerabilities
      </h3>
      <div className="hp-vuln-list-preview">
        {data.slice(0, 5).map((vuln) => (
          <div key={vuln.finding_id} className="hp-vuln-item-preview">
            <div className="hp-vuln-header-preview">
              <span
                className="hp-vuln-severity-badge"
                style={{
                  background: `${getSeverityColor(vuln.severity)}20`,
                  color: getSeverityColor(vuln.severity),
                }}
              >
                {vuln.severity.toUpperCase()}
              </span>
              <span className="hp-vuln-name-preview">{vuln.name}</span>
            </div>
            <p className="hp-vuln-desc-preview">{vuln.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function IOCList({ data }: { data: SecurityReport['iocs'] }) {
  if (!data?.length) return null;

  return (
    <div className="hp-preview-section">
      <h3>
        <List size={16} />
        Indicators of Compromise ({data.length})
      </h3>
      <div className="hp-ioc-list">
        {data.slice(0, 10).map((ioc, idx) => (
          <div key={idx} className="hp-ioc-item">
            <span className="hp-ioc-type">{ioc.ioc_type.toUpperCase()}</span>
            <code className="hp-ioc-value">{ioc.value}</code>
            <span className="hp-ioc-threat" style={{ color: getSeverityColor(ioc.threat_level) }}>
              {ioc.threat_level}
            </span>
            <span className="hp-ioc-confidence">{(ioc.confidence * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function Recommendations({ data }: { data: SecurityReport['recommendations'] }) {
  if (!data?.length) return null;

  return (
    <div className="hp-preview-section">
      <h3>
        <CheckCircle size={16} />
        Research Insights
      </h3>
      <ol className="hp-recommendations-list">
        {data.map((rec, idx) => (
          <li key={idx}>{rec}</li>
        ))}
      </ol>
    </div>
  );
}
