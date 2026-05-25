import { useState, useMemo } from 'react';
import { Fingerprint, AlertTriangle, ShieldCheck } from 'lucide-react';
import { AttackEvent } from '../types';
import './JA4Widget.css';

interface JA4WidgetProps {
  events: AttackEvent[];
  title?: string;
}

export function JA4Widget({ events, title = 'JA4 Fingerprint Analysis' }: JA4WidgetProps) {
  const [filter, setFilter] = useState<'all' | 'suspicious'>('all');

  // Aggregate JA4 fingerprints
  const fingerprints = useMemo(() => {
    const counts: Record<string, { count: number; malicious: boolean; last_seen: string }> = {};

    events.forEach((event) => {
      const ja4 = event.ja4_fingerprint || event.ja4h_fingerprint || event.ja4ssh_fingerprint;
      if (!ja4) return;

      if (!counts[ja4]) {
        counts[ja4] = {
          count: 0,
          malicious: event.severity === 'critical' || event.severity === 'high',
          last_seen: event.timestamp,
        };
      }
      counts[ja4].count++;
      if (event.severity === 'critical' || event.severity === 'high') {
        counts[ja4].malicious = true;
      }
      if (new Date(event.timestamp) > new Date(counts[ja4].last_seen)) {
        counts[ja4].last_seen = event.timestamp;
      }
    });

    return Object.entries(counts)
      .map(([ja4, data]) => ({ ja4, ...data }))
      .sort((a, b) => b.count - a.count);
  }, [events]);

  const displayedFingerprints =
    filter === 'all' ? fingerprints : fingerprints.filter((f) => f.malicious);

  return (
    <div className="ja4-widget-container">
      <div className="ja4-header">
        <div className="ja4-title-group">
          <Fingerprint className="ja4-icon" size={18} />
          <h3>{title}</h3>
        </div>
        <div className="ja4-controls">
          <button
            className={`ja4-filter-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          <button
            className={`ja4-filter-btn ${filter === 'suspicious' ? 'active' : ''}`}
            onClick={() => setFilter('suspicious')}
          >
            Suspicious Only
          </button>
        </div>
      </div>

      <div className="ja4-list">
        {displayedFingerprints.length === 0 ? (
          <div className="ja4-empty">No JA4 fingerprints captured yet.</div>
        ) : (
          displayedFingerprints.map((fp) => (
            <div key={fp.ja4} className={`ja4-item ${fp.malicious ? 'malicious' : ''}`}>
              <div className="ja4-item-header">
                <span className="ja4-hash" title={fp.ja4}>
                  {fp.ja4}
                </span>
                <span className="ja4-count-badge">{fp.count}</span>
              </div>
              <div className="ja4-item-meta">
                {fp.malicious ? (
                  <span className="ja4-tag danger">
                    <AlertTriangle size={12} /> High Risk
                  </span>
                ) : (
                  <span className="ja4-tag neutral">
                    <ShieldCheck size={12} /> Standard
                  </span>
                )}
                <span className="ja4-time">
                  Last seen: {new Date(fp.last_seen).toLocaleTimeString()}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
