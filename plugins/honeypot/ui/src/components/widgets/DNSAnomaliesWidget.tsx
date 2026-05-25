import { useState, useMemo } from 'react';
import { Activity, Globe, AlertOctagon } from 'lucide-react';
import { NetworkAnomaly } from '../types';
import './DNSAnomaliesWidget.css';

interface DNSAnomaliesWidgetProps {
  anomalies: NetworkAnomaly[];
}

export function DNSAnomaliesWidget({ anomalies }: DNSAnomaliesWidgetProps) {
  const [activeTab, setActiveTab] = useState<'dga' | 'flux' | 'nxdomain'>('dga');

  const stats = useMemo(() => {
    return {
      dga: anomalies.filter((a) => a.anomaly_type === 'dga').length,
      flux: anomalies.filter((a) => a.anomaly_type === 'fast_flux').length,
      nxdomain: anomalies.filter((a) => a.anomaly_type === 'nxdomain_burst').length,
    };
  }, [anomalies]);

  const filteredAnomalies = useMemo(() => {
    const typeMap: Record<string, string> = {
      dga: 'dga',
      flux: 'fast_flux',
      nxdomain: 'nxdomain_burst',
    };
    return anomalies.filter((a) => a.anomaly_type === typeMap[activeTab]);
  }, [anomalies, activeTab]);

  return (
    <div className="dns-widget-container">
      <div className="dns-header">
        <div className="dns-title">
          <Activity className="dns-icon" size={18} />
          <h3>DNS Anomalies</h3>
        </div>
      </div>

      <div className="dns-tabs">
        <div
          className={`dns-tab ${activeTab === 'dga' ? 'active' : ''}`}
          onClick={() => setActiveTab('dga')}
        >
          <span className="dns-tab-label">DGA</span>
          <span className="dns-tab-count">{stats.dga}</span>
        </div>
        <div
          className={`dns-tab ${activeTab === 'flux' ? 'active' : ''}`}
          onClick={() => setActiveTab('flux')}
        >
          <span className="dns-tab-label">Fast Flux</span>
          <span className="dns-tab-count">{stats.flux}</span>
        </div>
        <div
          className={`dns-tab ${activeTab === 'nxdomain' ? 'active' : ''}`}
          onClick={() => setActiveTab('nxdomain')}
        >
          <span className="dns-tab-label">NXDOMAIN</span>
          <span className="dns-tab-count">{stats.nxdomain}</span>
        </div>
      </div>

      <div className="dns-list">
        {filteredAnomalies.length === 0 ? (
          <div className="dns-empty">No anomalies detected in this category.</div>
        ) : (
          filteredAnomalies.map((anomaly) => (
            <div key={anomaly.anomaly_id} className="dns-item">
              <div className="dns-item-header">
                <span className="dns-item-title">
                  {activeTab === 'dga' ? <Globe size={14} /> : <AlertOctagon size={14} />}
                  {anomaly.metadata.domain || 'Unknown Domain'}
                </span>
                <span className={`dns-severity ${anomaly.severity}`}>{anomaly.severity}</span>
              </div>
              <div className="dns-item-desc">{anomaly.description}</div>
              <div className="dns-item-meta">
                <span>Confidence: {Math.round(anomaly.confidence * 100)}%</span>
                <span>{new Date(anomaly.detected_at).toLocaleTimeString()}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
