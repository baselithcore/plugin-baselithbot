/**
 * MonitorTab - Main monitoring view with stats, swarm graph, terminal, and events
 */

import { useRef, useState } from 'react';
import { Terminal, Eye, Target, Link, Globe, Activity, User, Key } from 'lucide-react';
import type { HoneypotStats, AttackEvent, DiscoveryLog } from '../../types';
import { normalizeIpDisplay } from '../../api';
import { getSeverityClass, getProtocolIcon } from '../utils';
import { getCountryFlag } from '../../geoUtils';
import HoneypotSwarmGraph from '../../HoneypotSwarmGraph';
import BotIndicator from '../../common/BotIndicator';
import ActiveSessionsModal from '../../ActiveSessionsModal';

interface MonitorTabProps {
  stats: HoneypotStats | null;
  logs: DiscoveryLog[];
  events: AttackEvent[];
  onSelectAttack: (event: AttackEvent) => void;
  /** When false, disables expensive canvas animations */
  isActive?: boolean;
}

export function MonitorTab({
  stats,
  logs,
  events,
  onSelectAttack,
  isActive = true,
}: MonitorTabProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const [showActiveSessions, setShowActiveSessions] = useState(false);

  // Auto-scroll to bottom of terminal
  // Auto-scroll removed to keep newest logs at top
  // useEffect(() => {
  //   if (terminalRef.current) {
  //     terminalRef.current.scrollTop = 0;
  //   }
  // }, [logs]);

  return (
    <div className="hp-monitor">
      {/* Stats Row */}
      <div className="hp-stats-row">
        <div className="hp-stat-card">
          <div className="hp-stat-icon">
            <Target size={32} color="#ff3366" />
          </div>
          <div className="hp-stat-content">
            <span className="hp-stat-value">{stats?.total_events || 0}</span>
            <span className="hp-stat-label">Total Attacks</span>
          </div>
        </div>
        <div
          className="hp-stat-card hp-interactive-card"
          onClick={() => setShowActiveSessions(true)}
        >
          <div className="hp-stat-icon">
            <Activity size={32} color="#00b4d8" />
          </div>
          <div className="hp-stat-content">
            <span className="hp-stat-value">{stats?.active_sessions || 0}</span>
            <span className="hp-stat-label">Active Sessions</span>
            <div style={{ position: 'absolute', top: '12px', right: '12px', opacity: 0.5 }}>
              <Link size={14} color="#00b4d8" />
            </div>
          </div>
        </div>
        <div className="hp-stat-card">
          <div className="hp-stat-icon">
            <Globe size={32} color="#26de81" />
          </div>
          <div className="hp-stat-content">
            <span className="hp-stat-value">{stats?.unique_ips || 0}</span>
            <span className="hp-stat-label">Unique IPs</span>
          </div>
        </div>
        <div className="hp-stat-card">
          <div className="hp-stat-icon">
            <Link size={32} color="#ffbe0b" />
          </div>
          <div className="hp-stat-content">
            <span className="hp-stat-value">{stats?.cve_correlations || 0}</span>
            <span className="hp-stat-label">CVE Matches</span>
          </div>
        </div>
      </div>

      {showActiveSessions && <ActiveSessionsModal onClose={() => setShowActiveSessions(false)} />}

      {/* Swarm Network Graph */}
      <HoneypotSwarmGraph
        logs={logs}
        stats={{
          ssh_handler: stats?.protocol_breakdown?.ssh || 0,
          http_handler: stats?.protocol_breakdown?.http || 0,
          tcp_handler: stats?.protocol_breakdown?.tcp || 0,
          correlator: stats?.cve_correlations || 0,
          responder: stats?.total_sessions || 0,
        }}
        isActive={isActive}
      />

      {/* Main Content */}
      <div className="hp-monitor-content">
        {/* Live Terminal */}
        <div
          className="hp-terminal-section"
          style={{ display: 'flex', flexDirection: 'column', gap: '0' }}
        >
          <div
            className="hp-terminal-header"
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '12px 16px',
              background: '#18181b', // Dark header
              borderTopLeftRadius: '12px',
              borderTopRightRadius: '12px',
              border: '1px solid #333',
              borderBottom: 'none',
            }}
          >
            {/* Restored Title with Icon */}
            <h3
              style={{
                margin: 0,
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '14px',
                fontWeight: 600,
                color: '#fff',
              }}
            >
              <Terminal size={16} color="#26de81" />
              Live Attack Feed
            </h3>
          </div>
          <div
            className="hp-terminal"
            ref={terminalRef}
            style={{
              background: '#09090b', // Deep black
              borderBottomLeftRadius: '12px',
              borderBottomRightRadius: '12px',
              border: '1px solid #333',
              flex: 1, // Fill available space
              minHeight: 0, // Critical for nested flex scrolling
              overflowY: 'auto',
              padding: '16px',
              fontFamily: 'Menlo, Monaco, Consolas, "Courier New", monospace',
              fontSize: '13px',
              color: '#26de81',
              boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
            }}
          >
            <div
              className="hp-terminal-content"
              style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}
            >
              {[...logs]
                .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
                .map((log, idx) => (
                  <div
                    key={idx}
                    className={`hp-log-entry ${log.is_alert ? 'alert' : ''} ${log.is_error ? 'error' : ''}`}
                    style={{
                      display: 'flex',
                      gap: '12px',
                      alignItems: 'baseline',
                      // Removed border-bottom for cleaner look
                      padding: '2px 0',
                    }}
                  >
                    <span
                      className="hp-log-time"
                      style={{
                        opacity: 0.4,
                        fontSize: '11px',
                        minWidth: '140px',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {(() => {
                        const d = new Date(log.timestamp);
                        // Added Date + Time as requested
                        return `${d.toLocaleDateString()} ${d.toLocaleTimeString()}`;
                      })()}
                    </span>
                    {log.country_code && (
                      <span
                        className="hp-log-flag"
                        title={log.country_code}
                        style={{ opacity: 0.8 }}
                      >
                        {getCountryFlag(log.country_code)}
                      </span>
                    )}
                    <span
                      className="hp-log-message"
                      style={{
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        color: log.is_error ? '#ff4757' : log.is_alert ? '#ffa502' : '#26de81',
                      }}
                    >
                      <span style={{ color: '#00b4d8', marginRight: '8px', fontWeight: 'bold' }}>
                        ❯
                      </span>
                      {log.message}
                    </span>
                  </div>
                ))}
              {logs.length === 0 && (
                <div
                  className="hp-terminal-empty"
                  style={{
                    opacity: 0.3,
                    fontStyle: 'italic',
                    textAlign: 'center',
                    marginTop: '40px',
                  }}
                >
                  _ system_ready. waiting for incoming signals...
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Recent Events */}
        <div className="hp-events-section">
          <div className="hp-section-header">
            <h3>
              <Eye size={16} /> Recent Attacks
            </h3>
          </div>
          <div className="hp-events-list">
            {events.slice(0, 10).map((event) => (
              <div
                key={event.event_id}
                className={`hp-event-card ${getSeverityClass(event.severity)}`}
                onClick={() => onSelectAttack(event)}
              >
                {/* Header: IP, Country, Bot Status */}
                <div className="hp-event-header-row">
                  <div className="hp-event-source">
                    <span className="hp-event-flag" title={event.geo?.country || 'Unknown Country'}>
                      {getCountryFlag(event.geo?.country_code || undefined)}
                    </span>
                    <span className="hp-event-ip">{normalizeIpDisplay(event.source_ip)}</span>
                  </div>

                  <div className="hp-event-meta-icons">
                    {/* Bot/Human Indicator */}
                    <div className="hp-actor-badge-wrapper">
                      <BotIndicator
                        isBot={event.is_bot}
                        confidence={event.bot_confidence}
                        signals={event.bot_signals}
                        size="small"
                        showLabel={false}
                      />
                    </div>

                    <span className={`hp-event-severity-badge ${getSeverityClass(event.severity)}`}>
                      {event.severity.toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Primary Info: Protocol & Category */}
                <div className="hp-event-primary-info">
                  <div className="hp-protocol-tag">
                    {getProtocolIcon(event.protocol)}
                    <span>{event.protocol.toUpperCase()}</span>
                  </div>
                  <div className="hp-category-tag">{event.category.replace(/_/g, ' ')}</div>
                </div>

                {/* Details: Command/Path */}
                {/* Details: Command/Path/Credentials */}
                {event.command || event.http_path || event.username || event.password ? (
                  <div className="hp-event-details">
                    {event.command && (
                      <div className="hp-detail-row command">
                        <span className="prompt">$</span>
                        <span className="content">{event.command}</span>
                      </div>
                    )}
                    {event.http_path && (
                      <div className="hp-detail-row path">
                        <span className="method">{event.http_method}</span>
                        <span className="content">{event.http_path}</span>
                      </div>
                    )}
                    {(event.username || event.password) && (
                      <div
                        className="hp-credentials-preview"
                        style={{
                          marginTop: '8px',
                          background: 'rgba(0, 0, 0, 0.2)',
                          borderRadius: '4px',
                          padding: '8px',
                          borderLeft: '2px solid #ffbe0b',
                        }}
                      >
                        {event.username && (
                          <div
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '8px',
                              marginBottom: event.password ? '4px' : '0',
                            }}
                          >
                            <User size={12} style={{ opacity: 0.5 }} />
                            <span
                              style={{
                                fontSize: '10px',
                                textTransform: 'uppercase',
                                letterSpacing: '0.5px',
                                opacity: 0.5,
                                minWidth: '60px',
                              }}
                            >
                              Username
                            </span>
                            <code
                              style={{
                                fontFamily: "'JetBrains Mono', monospace",
                                fontSize: '11px',
                                color: '#e0e0e0',
                              }}
                            >
                              {event.username}
                            </code>
                          </div>
                        )}
                        {event.password && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <Key size={12} style={{ opacity: 0.5 }} />
                            <span
                              style={{
                                fontSize: '10px',
                                textTransform: 'uppercase',
                                letterSpacing: '0.5px',
                                opacity: 0.5,
                                minWidth: '60px',
                              }}
                            >
                              Password
                            </span>
                            <code
                              style={{
                                fontFamily: "'JetBrains Mono', monospace",
                                fontSize: '11px',
                                color: '#ffbe0b',
                              }}
                            >
                              {event.password}
                            </code>
                          </div>
                        )}
                        <div
                          style={{
                            marginTop: '6px',
                            borderTop: '1px solid rgba(255, 255, 255, 0.1)',
                            paddingTop: '4px',
                            display: 'flex',
                            justifyContent: 'flex-end',
                          }}
                        >
                          <span
                            style={{
                              fontSize: '9px',
                              opacity: 0.4,
                              fontFamily: "'JetBrains Mono', monospace",
                            }}
                          >
                            {new Date(event.timestamp).toLocaleString([], {
                              year: 'numeric',
                              month: '2-digit',
                              day: '2-digit',
                              hour: '2-digit',
                              minute: '2-digit',
                              second: '2-digit',
                            })}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="hp-event-details empty">
                    <span className="hp-detail-placeholder">No payload captured</span>
                  </div>
                )}

                {/* Footer: CWES */}
                {event.matched_cwes.length > 0 && (
                  <div className="hp-event-footer">
                    <div className="hp-event-cwes">
                      {event.matched_cwes.slice(0, 3).map((cwe) => (
                        <span key={cwe} className="hp-cwe-badge">
                          {cwe}
                        </span>
                      ))}
                      {event.matched_cwes.length > 3 && (
                        <span className="hp-cwe-more">+{event.matched_cwes.length - 3}</span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
            {events.length === 0 && <div className="hp-no-events">No attacks captured yet</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
