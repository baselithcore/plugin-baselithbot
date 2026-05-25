/**
 * MonitorTab - Swarm Monitor Panel
 */

import { useCallback, useMemo } from 'react';
import { Activity, Bug, Search, Terminal, Zap } from 'lucide-react';

import type { CVEAgentStatus, CVEStats, SwarmStatus } from '../../types';
import type { DiscoveryLog, Finding } from '../types';
import DiscoveryNetwork from '../../DiscoveryNetwork';
import { getAgentIcon, getAgentActivity } from '../utils';

interface MonitorTabProps {
  swarmStatus: SwarmStatus | null;
  stats: CVEStats | null;
  agents: CVEAgentStatus[];
  discoveryLogs: DiscoveryLog[];
  findings: Finding[];
  isScanning: boolean;
  selectedAgentFilter: string | null;
  terminalRef: React.RefObject<HTMLDivElement>;
  terminalEndRef: React.RefObject<HTMLDivElement>;
  onAgentClick: (agentType: string) => void;
  onScan: () => void;
  onClearLogs: () => void;
  setSelectedAgentFilter: (filter: string | null) => void;
}

export const MonitorTab = ({
  swarmStatus,
  stats,
  agents,
  discoveryLogs,
  findings,
  isScanning,
  selectedAgentFilter,
  terminalRef,
  terminalEndRef,
  onAgentClick,
  onScan,
  onClearLogs,
  setSelectedAgentFilter,
}: MonitorTabProps) => {
  // Memoize filtered logs
  const filteredLogs = useMemo(() => {
    if (!selectedAgentFilter) return discoveryLogs;

    return discoveryLogs.filter((log) => {
      const msg = log.message.toUpperCase();
      const filter = selectedAgentFilter.toUpperCase();

      if (filter === 'SYSTEM') {
        return (
          !msg.includes('SCANNER:') && !msg.includes('ANALYZER:') && !msg.includes('DISCOVERY:')
        );
      }

      return msg.includes(filter);
    });
  }, [discoveryLogs, selectedAgentFilter]);

  const handleAgentClick = useCallback(
    (agentType: string) => {
      onAgentClick(agentType);
    },
    [onAgentClick]
  );

  return (
    <div className="cve-main-grid">
      {/* Sidebar */}
      <aside className="cve-sidebar">
        {/* Swarm Status Card */}
        <div className="cyber-card">
          <h2>
            <Activity size={14} /> SWARM AGENTS
          </h2>
          <div className="agent-list">
            {agents.map((agent) => (
              <div
                key={agent.agent_id}
                className={`agent-item ${agent.status !== 'idle' ? 'active' : ''} ${
                  selectedAgentFilter === agent.agent_type ? 'selected-filter' : ''
                }`}
                onClick={() => handleAgentClick(agent.agent_type)}
                style={{
                  cursor: 'pointer',
                  border:
                    selectedAgentFilter === agent.agent_type
                      ? '1px solid var(--cyber-neon-green)'
                      : '',
                }}
                title="Click to filter logs"
              >
                <span className="agent-icon">{getAgentIcon(agent.agent_type)}</span>
                <div className="agent-info">
                  <div className="agent-name">
                    {agent.agent_type.charAt(0).toUpperCase() + agent.agent_type.slice(1)}
                  </div>
                  <div className={`agent-status ${agent.status !== 'idle' ? 'active' : ''}`}>
                    {agent.status.toUpperCase()}
                  </div>
                </div>
                {selectedAgentFilter === agent.agent_type && (
                  <span style={{ fontSize: '10px', color: 'var(--cyber-neon-green)' }}>
                    FILTER ACTIVE
                  </span>
                )}
              </div>
            ))}
          </div>

          {/* Mini stats */}
          <div className="stats-mini-grid">
            <div className="stat-mini">
              <div className="stat-mini-value">{swarmStatus?.active_agents ?? 0}</div>
              <div className="stat-mini-label">Active</div>
            </div>
            <div className="stat-mini">
              <div className="stat-mini-value">{swarmStatus?.queued_tasks ?? 0}</div>
              <div className="stat-mini-label">Queued</div>
            </div>
            <div className="stat-mini">
              <div className="stat-mini-value">{swarmStatus?.completed_tasks ?? 0}</div>
              <div className="stat-mini-label">Done</div>
            </div>
            <div className="stat-mini">
              <div className="stat-mini-value">{stats?.active_alerts ?? 0}</div>
              <div className="stat-mini-label">Alerts</div>
            </div>
          </div>

          {/* Scan button */}
          <button className="scan-button" onClick={onScan} disabled={isScanning}>
            {isScanning ? (
              <>⏳ SCANNING...</>
            ) : (
              <>
                <Search size={16} /> INITIATE SCAN
              </>
            )}
          </button>
        </div>

        {/* Activity Section */}
        <div className="cyber-card activity-section">
          <h2>
            <Zap size={14} /> AGENT ACTIVITY
          </h2>
          <div className="activity-bars">
            {agents.map((agent) => (
              <div key={agent.agent_id} className="activity-bar">
                <span className="activity-label">{agent.agent_type}</span>
                <div className="progress-track">
                  <div
                    className={`progress-fill ${agent.agent_type}`}
                    style={{ width: `${getAgentActivity(agent)}%` }}
                  />
                </div>
                <span className="activity-percent">{getAgentActivity(agent)}%</span>
              </div>
            ))}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="cve-content">
        {/* Network Graph */}
        <DiscoveryNetwork logs={discoveryLogs} />

        {/* Bottom Section */}
        <div className="cve-monitor-bottom-row">
          {/* Live Hunt Terminal */}
          <div className="cve-terminal-section" style={{ marginTop: 0, height: '100%' }}>
            <header className="cve-terminal-header">
              <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Terminal size={14} /> Live Hunt Protocol Active
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {/* Log Filters */}
                {['ALL', 'DISCOVERY', 'SCANNER', 'ANALYZER', 'SYSTEM'].map((filter) => (
                  <button
                    key={filter}
                    onClick={() =>
                      setSelectedAgentFilter(filter === 'ALL' ? null : filter.toLowerCase())
                    }
                    style={{
                      background: 'transparent',
                      border:
                        (selectedAgentFilter === null && filter === 'ALL') ||
                        selectedAgentFilter === filter.toLowerCase()
                          ? '1px solid var(--cyber-neon-green)'
                          : '1px solid #333',
                      color:
                        (selectedAgentFilter === null && filter === 'ALL') ||
                        selectedAgentFilter === filter.toLowerCase()
                          ? 'var(--cyber-neon-green)'
                          : '#666',
                      fontSize: '9px',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                    }}
                  >
                    {filter}
                  </button>
                ))}
                <div
                  style={{ width: '1px', height: '12px', background: '#333', margin: '0 4px' }}
                />
                <button
                  onClick={onClearLogs}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#666',
                    fontSize: '10px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                  title="Clear terminal logs"
                >
                  CLEAR_LOGS
                </button>
              </div>
            </header>
            <div
              style={{
                position: 'relative',
                flex: 1,
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <div className="terminal-scanline" />
              <div className="cve-terminal-body" ref={terminalRef}>
                {[...filteredLogs].reverse().map((log, index) => {
                  let agentClass = 'log-system';
                  const msg = log.message.toUpperCase();
                  if (msg.includes('SCANNER:')) agentClass = 'log-scanner';
                  else if (msg.includes('ANALYZER:')) agentClass = 'log-analyzer';
                  else if (msg.includes('DISCOVERY:')) agentClass = 'log-discovery';

                  return (
                    <div key={index} className={`terminal-line ${agentClass}`}>
                      <span className="timestamp">
                        [{new Date(log.timestamp).toLocaleTimeString()}]
                      </span>
                      <span
                        className={`message ${log.is_alert ? 'alert' : ''} ${
                          log.is_error ? 'error' : ''
                        }`}
                      >
                        {log.message}
                      </span>
                    </div>
                  );
                })}
                {filteredLogs.length === 0 && (
                  <div className="terminal-line" style={{ opacity: 0.5 }}>
                    Waiting for agent activity...
                  </div>
                )}
                <div className="terminal-line cve-term-cursor" style={{ opacity: 0.5 }}>
                  <span className="timestamp">[{new Date().toLocaleTimeString()}]</span>
                  <span className="message">SYSTEM_READY</span>
                </div>
                <div ref={terminalEndRef} />
              </div>
              <div className="terminal-status-bar">
                <span>REGION: EU-WEST-1</span>
                <span className="terminal-status-ready">STATUS: ONLINE</span>
                <span>ENC: AES-256</span>
              </div>
            </div>
          </div>

          {/* Live Findings Panel */}
          <div
            className="cyber-card"
            style={{
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            <header
              className="cve-terminal-header"
              style={{
                marginBottom: '10px',
                borderBottom: '1px solid #333',
                paddingBottom: '10px',
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '4px',
              }}
            >
              <span
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  color: 'var(--cyber-neon-pink)',
                }}
              >
                <Bug size={14} /> Live Findings
              </span>
              <span style={{ fontSize: '10px', color: '#888', marginLeft: '22px' }}>
                Raw anomalies detected by Discovery Agent before verification.
              </span>
            </header>
            <div style={{ flex: 1, overflowY: 'auto', paddingRight: '5px' }}>
              {findings.length > 0 ? (
                findings.map((finding, i) => (
                  <div
                    key={i}
                    style={{
                      padding: '10px',
                      background: 'rgba(255, 0, 128, 0.05)',
                      borderLeft: '2px solid var(--cyber-neon-pink)',
                      marginBottom: '10px',
                      fontSize: '12px',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        marginBottom: '4px',
                      }}
                    >
                      <span style={{ color: 'var(--cyber-neon-pink)', fontWeight: 'bold' }}>
                        {finding.pattern ? finding.pattern.toUpperCase() : 'UNKNOWN ANOMALY'}
                      </span>
                      <span style={{ opacity: 0.5 }}>
                        {finding.timestamp
                          ? new Date(finding.timestamp).toLocaleTimeString()
                          : 'RECENT'}
                      </span>
                    </div>
                    <div style={{ opacity: 0.8, marginBottom: '4px' }}>
                      {finding.context || 'Potential vulnerability detected during analysis.'}
                    </div>
                    <div style={{ display: 'flex', gap: '10px', fontSize: '10px', opacity: 0.6 }}>
                      <span>
                        Confidence:{' '}
                        {finding.confidence ? (finding.confidence * 100).toFixed(0) + '%' : 'N/A'}
                      </span>
                      <span>Source: {finding.source || 'Unknown'}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div
                  style={{
                    textAlign: 'center',
                    padding: '20px',
                    opacity: 0.5,
                    fontSize: '12px',
                  }}
                >
                  <i>Waiting for new discoveries...</i>
                </div>
              )}
              <div style={{ textAlign: 'center', padding: '10px', opacity: 0.3, fontSize: '10px' }}>
                <i>Swarm is actively monitoring online sources for zero-days...</i>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
