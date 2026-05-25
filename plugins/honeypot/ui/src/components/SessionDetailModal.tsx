import { useEffect, useState } from 'react';
import {
  X,
  Globe,
  Terminal,
  Activity,
  Clock,
  MapPin,
  Hash,
  Server,
  User,
  FileText,
  AlertTriangle,
  Brain,
  Sparkles,
} from 'lucide-react';
import type { HoneypotSession } from './types';
import * as api from './api';
import { normalizeIpDisplay } from './api';
import ExpandableSection from './common/ExpandableSection';
import CopyButton from './common/CopyButton';
import './HoneypotPanel.css';

interface SessionDetailModalProps {
  sessionId: string;
  onClose: () => void;
}

export default function SessionDetailModal({ sessionId, onClose }: SessionDetailModalProps) {
  const [session, setSession] = useState<HoneypotSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadSession = async () => {
      try {
        setIsLoading(true);
        const data = await api.fetchSessionDetail(sessionId);
        setSession(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load session details');
      } finally {
        setIsLoading(false);
      }
    };
    loadSession();
  }, [sessionId]);

  if (isLoading) {
    return (
      <div className="hp-modal-overlay">
        <div className="hp-premium-modal">
          <div className="hp-loading-state">
            <div className="hp-spinner"></div>
            <span>Loading session details...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="hp-modal-overlay">
        <div className="hp-premium-modal">
          <div className="hp-error-state">
            <AlertTriangle size={48} />
            <h3>Failed to load session</h3>
            <p>{error || 'Session data not found'}</p>
            <button className="hp-btn-primary" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </div>
    );
  }

  const duration = session.duration_seconds ? `${session.duration_seconds}s` : 'Active';

  return (
    <div className="hp-modal-overlay" onClick={onClose}>
      <div
        className="hp-premium-modal hp-premium-modal--enhanced"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <header className="hp-glass-header">
          <div className="hp-header-left">
            <div className="hp-icon-badge">
              <Activity size={24} />
            </div>
            <div className="hp-header-info">
              <div className="hp-overline">Session Detail</div>
              <h2>{session.primary_category.replace('_', ' ').toUpperCase()}</h2>
            </div>
          </div>

          <div className="hp-header-right">
            <div className="hp-severity-badge-large">
              <span className="label">Severity</span>
              <span
                className="value"
                style={{ color: `var(--cyber-${session.max_severity.toLowerCase()})` }}
              >
                {session.max_severity.toUpperCase()}
              </span>
            </div>
            <button className="hp-close-btn" onClick={onClose}>
              <X size={20} />
            </button>
          </div>
        </header>

        <div className="hp-modal-body">
          <div className="hp-modal-grid">
            {/* Left Column */}
            <div className="hp-column-left">
              {/* Source Info */}
              <ExpandableSection title="Source Intelligence" icon={<Globe size={16} />}>
                <div className="hp-detail-card hp-geo-card">
                  <div className="hp-geo-main">
                    <div className="hp-geo-info">
                      <div className="hp-detail-value hp-detail-value--large">
                        {normalizeIpDisplay(session.source_ip)}
                        <CopyButton text={session.source_ip} label="Copy IP" />
                      </div>
                      <div className="hp-detail-label">
                        {session.geo?.city ? `${session.geo.city}, ` : ''}
                        {session.geo?.country || 'Unknown Country'}
                      </div>
                      {session.geo?.latitude && session.geo?.longitude && (
                        <div className="hp-geo-coords">
                          {session.geo.latitude.toFixed(4)}, {session.geo.longitude.toFixed(4)}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="hp-geo-tags">
                    {session.geo?.country_code && (
                      <span className="hp-tag">
                        <MapPin size={10} /> {session.geo.country_code}
                      </span>
                    )}
                  </div>
                </div>
              </ExpandableSection>

              {/* Commands */}
              {session.commands && session.commands.length > 0 && (
                <ExpandableSection title="Executed Commands" icon={<Terminal size={16} />}>
                  <div className="hp-payload-box">
                    <div className="hp-payload-content hp-payload-content--full">
                      {session.commands.map((cmd, idx) => (
                        <div key={idx} className="hp-command-row">
                          <span className="hp-prompt">$</span>
                          <span className="hp-command-text">{cmd}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </ExpandableSection>
              )}

              {/* Accessed Paths */}
              {session.paths_accessed && session.paths_accessed.length > 0 && (
                <ExpandableSection title="Accessed Paths" icon={<FileText size={16} />}>
                  <div className="hp-payload-box">
                    <div className="hp-payload-content hp-payload-content--full">
                      {session.paths_accessed.map((path, idx) => (
                        <div key={idx} className="hp-path-row">
                          {path}
                        </div>
                      ))}
                    </div>
                  </div>
                </ExpandableSection>
              )}
            </div>

            {/* Right Column */}
            <div className="hp-column-right">
              <ExpandableSection title="Session Metadata" icon={<Hash size={16} />}>
                <div className="hp-meta-list">
                  <div className="hp-meta-item">
                    <Clock size={16} />
                    <div className="hp-meta-content">
                      <label>Started At</label>
                      <span>{new Date(session.started_at).toLocaleString()}</span>
                    </div>
                  </div>
                  <div className="hp-meta-item">
                    <Activity size={16} />
                    <div className="hp-meta-content">
                      <label>Duration</label>
                      <span>{duration}</span>
                    </div>
                  </div>
                  <div className="hp-meta-item">
                    <Server size={16} />
                    <div className="hp-meta-content">
                      <label>Protocol</label>
                      <span>{session.protocol.toUpperCase()}</span>
                    </div>
                  </div>
                  <div className="hp-meta-item">
                    <FileText size={16} />
                    <div className="hp-meta-content">
                      <label>Session ID</label>
                      <span className="hp-meta-value--mono">
                        {session.session_id.substring(0, 12)}...
                        <CopyButton text={session.session_id} />
                      </span>
                    </div>
                  </div>
                  {session.username && (
                    <div className="hp-meta-item">
                      <User size={16} />
                      <div className="hp-meta-content">
                        <label>Username</label>
                        <span>{session.username}</span>
                      </div>
                    </div>
                  )}
                </div>
              </ExpandableSection>

              {/* Stats */}
              <ExpandableSection title="Activity Stats" icon={<Activity size={16} />}>
                <div className="hp-stats-grid-mini">
                  <div className="hp-stat-mini">
                    <div className="label">Auth Attempts</div>
                    <div className="value">{session.auth_attempts}</div>
                  </div>
                  <div className="hp-stat-mini">
                    <div className="label">Auth Success</div>
                    <div className={`value ${session.auth_success ? 'danger' : ''}`}>
                      {session.auth_success ? 'YES' : 'NO'}
                    </div>
                  </div>
                </div>
              </ExpandableSection>

              {/* Security Analysis / CVEs */}
              {session.matched_cves && session.matched_cves.length > 0 && (
                <ExpandableSection title="Matched CVEs" icon={<AlertTriangle size={16} />}>
                  <div className="hp-cve-list">
                    {session.matched_cves.map((cve) => (
                      <div key={cve} className="hp-cve-badge">
                        {cve}
                      </div>
                    ))}
                  </div>
                </ExpandableSection>
              )}
            </div>
          </div>

          {/* AI Summary */}
          {session.ai_summary && (
            <div className="hp-ai-section">
              <div className="hp-ai-header">
                <div className="hp-ai-label">
                  <Brain size={16} /> AI Session Analysis
                </div>
              </div>
              <div className="hp-ai-card analyzed">
                <div className="hp-ai-content">
                  <div className="hp-ai-result">
                    <Sparkles className="hp-ai-sparkle" size={16} />
                    <p>{session.ai_summary}</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
