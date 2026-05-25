/**
 * RDNSPanel - Reverse DNS Intelligence Panel
 *
 * Displays RDNS-enriched IP data with significance scoring
 * and domain categorization for threat analysis.
 */

import { useEffect, useState, useCallback } from 'react';
import {
  Globe,
  RefreshCw,
  Filter,
  AlertTriangle,
  Shield,
  Server,
  Wifi,
  HelpCircle,
  ExternalLink,
  Clock,
  Database,
} from 'lucide-react';
import { fetchRDNSData, RDNSEnrichmentResponse } from '../../../../api/discovery';

import './RDNSPanel.css';

interface RDNSPanelProps {
  honeypotId?: string | null;
}

type ImportanceFilter = 'all' | 'high' | 'medium' | 'low';

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  crawler: <Globe size={14} className="category-icon crawler" />,
  vpn_proxy: <Shield size={14} className="category-icon vpn" />,
  hosting: <Server size={14} className="category-icon hosting" />,
  isp: <Wifi size={14} className="category-icon isp" />,
  malicious: <AlertTriangle size={14} className="category-icon malicious" />,
  unknown: <HelpCircle size={14} className="category-icon unknown" />,
};

const CATEGORY_LABELS: Record<string, string> = {
  crawler: 'Crawler',
  vpn_proxy: 'VPN/Proxy',
  hosting: 'Hosting',
  isp: 'ISP',
  malicious: 'Malicious',
  unknown: 'Unknown',
};

export function RDNSPanel({ honeypotId }: RDNSPanelProps) {
  const [data, setData] = useState<RDNSEnrichmentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<ImportanceFilter>('all');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const minImportance = filter === 'all' ? 'low' : filter;
      const response = await fetchRDNSData(honeypotId || undefined, minImportance, 200);
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load RDNS data');
    } finally {
      setLoading(false);
    }
  }, [honeypotId, filter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const filteredResults =
    data?.results.filter((r: { importance: string }) => {
      if (filter === 'all') return true;
      return r.importance === filter;
    }) || [];

  const getImportanceBadge = (importance: string) => {
    const classes = `importance-badge ${importance}`;
    return <span className={classes}>{importance.toUpperCase()}</span>;
  };

  const getCategoryDisplay = (category: string | null) => {
    const cat = category || 'unknown';
    return (
      <span className="category-display">
        {CATEGORY_ICONS[cat] || CATEGORY_ICONS.unknown}
        <span className="category-label">{CATEGORY_LABELS[cat] || 'Unknown'}</span>
      </span>
    );
  };

  return (
    <div className="rdns-panel">
      {/* Header */}
      <div className="rdns-header">
        <div className="rdns-title">
          <Globe size={18} />
          <h3>RDNS Intelligence</h3>
          {data && (
            <span className="rdns-stats">
              {data.resolved_count} resolved / {data.total} total
            </span>
          )}
        </div>

        <div className="rdns-controls">
          {/* Filter Dropdown */}
          <div className="filter-dropdown">
            <Filter size={14} />
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as ImportanceFilter)}
              className="filter-select"
            >
              <option value="all">All Importance</option>
              <option value="high">High Only</option>
              <option value="medium">Medium+</option>
              <option value="low">Low+</option>
            </select>
          </div>

          {/* Refresh Button */}
          <button
            className="refresh-btn"
            onClick={loadData}
            disabled={loading}
            title="Refresh RDNS data"
          >
            <RefreshCw size={14} className={loading ? 'spinning' : ''} />
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      {data && (
        <div className="rdns-stats-bar">
          <div className="stat-item">
            <Clock size={12} />
            <span>{data.processing_time_ms.toFixed(0)}ms</span>
          </div>
          <div className="stat-item">
            <Database size={12} />
            <span>{data.cached_count} cached</span>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="rdns-error">
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Loading State */}
      {loading && !data && (
        <div className="rdns-loading">
          <RefreshCw size={24} className="spinning" />
          <p>Resolving hostnames...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && data && filteredResults.length === 0 && (
        <div className="rdns-empty">
          <Globe size={32} />
          <p>No RDNS results match the current filter.</p>
          <button onClick={() => setFilter('all')}>Show All</button>
        </div>
      )}

      {/* Results Table */}
      {filteredResults.length > 0 && (
        <div className="rdns-table-container">
          <table className="rdns-table">
            <thead>
              <tr>
                <th>IP Address</th>
                <th>Hostname</th>
                <th>Importance</th>
                <th>Category</th>
                <th>Organization</th>
              </tr>
            </thead>
            <tbody>
              {filteredResults.map((result: any) => (
                <tr key={result.ip} className={`row-${result.importance}`}>
                  <td className="ip-cell">
                    <code>{result.ip}</code>
                    {result.cached && (
                      <span className="cached-badge" title="Cached result">
                        C
                      </span>
                    )}
                  </td>
                  <td className="hostname-cell">
                    {result.hostname ? (
                      <span className="hostname">
                        {result.hostname}
                        <a
                          href={`https://who.is/whois/${result.hostname}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="whois-link"
                          title="WHOIS lookup"
                        >
                          <ExternalLink size={12} />
                        </a>
                      </span>
                    ) : (
                      <span className="no-hostname">
                        {result.error ? `Error: ${result.error}` : 'No PTR record'}
                      </span>
                    )}
                  </td>
                  <td className="importance-cell">{getImportanceBadge(result.importance)}</td>
                  <td className="category-cell">{getCategoryDisplay(result.category)}</td>
                  <td className="org-cell">{result.org || result.asn || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
