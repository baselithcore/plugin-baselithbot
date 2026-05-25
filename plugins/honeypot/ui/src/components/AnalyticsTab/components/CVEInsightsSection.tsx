import { TrendingUp } from 'lucide-react';

interface TopMatchedCVE {
  cve_id: string;
  count: number;
}

interface CVEInsightsSectionProps {
  cveCorrelations: number;
  topMatchedCves: TopMatchedCVE[];
  onCVEClick: (e: React.MouseEvent, cve: string) => void;
  onViewDetails: () => void;
}

export function CVEInsightsSection({
  cveCorrelations,
  topMatchedCves,
  onCVEClick,
  onViewDetails,
}: CVEInsightsSectionProps) {
  return (
    <div className="analytics-section-card cve-insights">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '12px',
        }}
      >
        <h3 className="analytics-section-title" style={{ margin: 0 }}>
          <TrendingUp size={18} /> CVE Correlations
        </h3>
        {cveCorrelations > 0 && (
          <a
            href="#"
            onClick={(e) => {
              e.preventDefault();
              onViewDetails();
            }}
            style={{
              color: '#a55eea',
              fontSize: '0.85rem',
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            View Details →
          </a>
        )}
      </div>
      <div className="analytics-cve-content">
        <div className="analytics-cve-stat">
          <span className="analytics-cve-number">{cveCorrelations || 0}</span>
          <span className="analytics-cve-label">Total Matches</span>
        </div>
        <div className="analytics-cve-stat" style={{ marginTop: '8px', opacity: 0.8 }}>
          <span className="analytics-cve-number" style={{ fontSize: '1.5rem' }}>
            {topMatchedCves?.length || 0}
          </span>
          <span className="analytics-cve-label" style={{ fontSize: '0.75rem' }}>
            Unique CVEs
          </span>
        </div>
        <div className="analytics-cve-list" style={{ marginTop: '16px' }}>
          {topMatchedCves?.slice(0, 5).map((cve, idx) => (
            <a
              key={idx}
              className="analytics-cve-item"
              href="#"
              onClick={(e) => onCVEClick(e, cve.cve_id)}
              style={{
                textDecoration: 'none',
                cursor: 'pointer',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '8px 12px',
                background: 'rgba(165, 94, 234, 0.1)',
                borderRadius: '6px',
                marginBottom: '6px',
                border: '1px solid rgba(165, 94, 234, 0.2)',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(165, 94, 234, 0.2)';
                e.currentTarget.style.borderColor = 'rgba(165, 94, 234, 0.4)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(165, 94, 234, 0.1)';
                e.currentTarget.style.borderColor = 'rgba(165, 94, 234, 0.2)';
              }}
            >
              <span className="analytics-cve-id" style={{ color: '#a55eea', fontWeight: 600 }}>
                {cve.cve_id}
              </span>
              <span
                className="analytics-cve-count"
                style={{
                  background: 'rgba(165, 94, 234, 0.3)',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                }}
              >
                {cve.count}×
              </span>
            </a>
          ))}
          {(!topMatchedCves || topMatchedCves.length === 0) && (
            <div
              className="analytics-empty-small"
              style={{
                textAlign: 'center',
                padding: '24px',
                color: '#8892b0',
                fontSize: '0.9rem',
              }}
            >
              No CVE correlations detected yet
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
