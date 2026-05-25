import { useState, useEffect } from 'react';
import { X, Clock, Terminal, Globe, Radio, Ban, Activity, RefreshCw } from 'lucide-react';
import type { HoneypotSession } from './types';
import * as api from './api';
import { normalizeIpDisplay } from './api';
import { getCountryFlag } from './geoUtils';
import SessionDetailModal from './SessionDetailModal';
import './ActiveSessionsModal.css';

interface ActiveSessionsModalProps {
  onClose: () => void;
}

export default function ActiveSessionsModal({ onClose }: ActiveSessionsModalProps) {
  const [sessions, setSessions] = useState<HoneypotSession[]>([]);
  const [totalActive, setTotalActive] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

  useEffect(() => {
    const loadSessions = async () => {
      try {
        // Fetch up to 100 active sessions
        const response = await api.fetchSessions(1, 100, { active_only: true });
        setSessions(response.items);
        // The API returns the true count of active sessions in the 'active' field
        setTotalActive(response.active);
        setIsLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load sessions');
        setIsLoading(false);
      }
    };
    loadSessions();
    const interval = setInterval(loadSessions, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, []);

  const getProtocolIcon = (protocol: string) => {
    switch (protocol?.toLowerCase()) {
      case 'ssh':
        return <Terminal size={18} color="#f59e0b" />;
      case 'http':
      case 'https':
        return <Globe size={18} color="#3b82f6" />;
      case 'tcp':
        return <Radio size={18} color="#8b5cf6" />;
      default:
        return <Ban size={18} color="#64748b" />;
    }
  };

  const calculateDuration = (startedAt: string) => {
    const start = new Date(startedAt).getTime();
    const now = new Date().getTime();
    const diff = Math.floor((now - start) / 1000);

    if (diff < 60) return `${diff}s`;
    const mins = Math.floor(diff / 60);
    if (mins < 60) return `${mins}m`;
    const hours = Math.floor(mins / 60);
    return `${hours}h ${mins % 60}m`;
  };

  return (
    <>
      <div className="hp-active-sessions-modal-overlay">
        <div className="hp-active-sessions-modal">
          {/* Header */}
          <div className="hp-asm-header">
            <div className="hp-asm-title-group">
              <div className="hp-asm-pulse" />
              <h2 className="hp-asm-title">
                Active Sessions
                <span className="hp-asm-count">{totalActive}</span>
              </h2>
            </div>
            <button onClick={onClose} className="hp-asm-close-btn">
              <X size={20} />
            </button>
          </div>

          {/* Content */}
          <div className="hp-asm-content">
            {isLoading && sessions.length === 0 ? (
              <div className="hp-asm-message">
                <RefreshCw className="animate-spin" size={24} style={{ marginBottom: 10 }} />
                <div>Loading active sessions...</div>
              </div>
            ) : error ? (
              <div className="hp-asm-error">{error}</div>
            ) : sessions.length === 0 ? (
              <div className="hp-asm-message">No active sessions currently</div>
            ) : (
              sessions.map((session) => (
                <div
                  key={session.session_id}
                  className="hp-asm-item"
                  onClick={() => setSelectedSessionId(session.session_id)}
                >
                  {/* Left: Identity */}
                  <div className="hp-asm-item-left">
                    <div className="hp-asm-proto-icon">{getProtocolIcon(session.protocol)}</div>
                    <div className="hp-asm-identity">
                      <div className="hp-asm-ip-row">
                        <span className="hp-asm-flag" title={session.geo?.country || 'Unknown'}>
                          {getCountryFlag(session.geo?.country_code || undefined)}
                        </span>
                        <span className="hp-asm-ip">{normalizeIpDisplay(session.source_ip)}</span>
                      </div>
                      <div className="hp-asm-id">{session.session_id}</div>
                    </div>
                  </div>

                  {/* Right: Metrics */}
                  <div className="hp-asm-item-right">
                    <div className="hp-asm-metric">
                      <span className="hp-asm-label">Events</span>
                      <span className="hp-asm-value events">
                        <Activity size={12} />
                        {session.events_count}
                      </span>
                    </div>
                    <div className="hp-asm-metric">
                      <span className="hp-asm-label">Duration</span>
                      <span className="hp-asm-value time">
                        <Clock size={12} />
                        {calculateDuration(session.started_at)}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          {sessions.length > 0 && (
            <div className="hp-asm-footer">
              <div className="hp-asm-footer-info">
                Showing {sessions.length} of {totalActive} active sessions
              </div>
              {sessions.length < totalActive && (
                <div style={{ fontStyle: 'italic', opacity: 0.7 }}>
                  (List truncated for performance)
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {selectedSessionId && (
        <SessionDetailModal
          sessionId={selectedSessionId}
          onClose={() => setSelectedSessionId(null)}
        />
      )}
    </>
  );
}
