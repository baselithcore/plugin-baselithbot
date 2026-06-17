/**
 * HoneypotPanel - Main Dashboard Component
 *
 * Refactored to use modular hooks and tab components.
 * Now supports per-honeypot visualization with honeypot selector.
 */

import { useState, useMemo, useEffect, useCallback } from 'react';
import {
  Wifi,
  WifiOff,
  Terminal,
  BarChart3,
  AlertTriangle,
  Globe,
  LogOut,
  Shield,
  Network,
  FileText,
} from 'lucide-react';
import type { AttackEvent, HoneypotInfo, HoneypotAttacker } from '../types';

import { useHoneypotData, useHoneypotSSE } from './hooks';
import { TabType } from './types';
import { MonitorTab, GlobeTab, ThreatsTab, PentestTab, DiscoveryTab, ReportsTab } from './tabs';
import { useAuth } from '@auth';

import AttackDetailModal from '../AttackDetailModal';
import AnalyticsTab from '../AnalyticsTab';
import { fetchHoneypots, fetchAllAttackers } from '../api';

import './HoneypotPanel.css';

const maskEmail = (email: string): string => {
  if (!email || !email.includes('@')) return email;
  const lastAt = email.lastIndexOf('@');
  const name = email.slice(0, lastAt);
  const domain = email.slice(lastAt + 1);

  if (name.length <= 3) {
    return `${name[0]}***@${domain}`;
  }
  return `${name.slice(0, 3)}***@${domain}`;
};

const ALL_TABS: { id: TabType; icon: any; label: string }[] = [
  { id: 'monitor', icon: Terminal, label: 'Monitor' },
  { id: 'globe', icon: Globe, label: 'Globe' },
  { id: 'analytics', icon: BarChart3, label: 'Analytics' },
  { id: 'threats', icon: AlertTriangle, label: 'Threats' },
  { id: 'pentest', icon: Shield, label: 'Pentest' },
  { id: 'discovery', icon: Network, label: 'Discovery' },
  { id: 'reports', icon: FileText, label: 'Reports' },
];

const HoneypotPanel = () => {
  // Data fetching hook
  const [selectedHoneypotId, setSelectedHoneypotId] = useState<string | null>(null);

  // Auth hook
  const { logout, user, canAccessTab } = useAuth();

  // Filter visible tabs based on the central RBAC policy (scoped to honeypot).
  const visibleTabs = useMemo(() => {
    return ALL_TABS.filter((tab) => canAccessTab(tab.id, 'honeypot'));
  }, [canAccessTab]);

  // Ensure active tab is always valid
  const [activeTab, setActiveTab] = useState<TabType>(() => {
    // Initial state: use first visible tab or fallback to 'monitor'
    const firstVisible = ALL_TABS.find((t) => canAccessTab(t.id, 'honeypot'));
    return firstVisible ? firstVisible.id : 'monitor';
  });

  // Redirect if current tab becomes inaccessible
  useEffect(() => {
    if (!canAccessTab(activeTab, 'honeypot') && visibleTabs.length > 0) {
      setActiveTab(visibleTabs[0].id);
    }
  }, [activeTab, canAccessTab, visibleTabs]);

  const [selectedAttack, setSelectedAttack] = useState<AttackEvent | null>(null);

  // Honeypot selection state
  const [honeypots, setHoneypots] = useState<HoneypotInfo[]>([]);
  const [honeypotsLoading, setHoneypotsLoading] = useState(true);

  // Attackers state for Globe visualization (persistent nodes)
  const [attackers, setAttackers] = useState<HoneypotAttacker[]>([]);
  // Time range state for Globe visualization (default last 24h)
  const [timeRange, setTimeRange] = useState<string>('24h');

  const { status, stats, events, logs, isLoading, error, setStats, setEvents, setLogs } =
    useHoneypotData(5000);

  // SSE real-time updates
  useHoneypotSSE({ setEvents, setStats, setLogs, setHoneypots });

  // Fetch honeypots on mount
  useEffect(() => {
    const loadHoneypots = async () => {
      try {
        setHoneypotsLoading(true);
        const data = await fetchHoneypots();
        setHoneypots(data);
        // Do not auto-select first honeypot - allow "All" view by default
        // if (data.length > 0 && !selectedHoneypotId) {
        //   setSelectedHoneypotId(data[0].id);
        // }
      } catch (err) {
        console.error('Failed to fetch honeypots:', err);
      } finally {
        setHoneypotsLoading(false);
      }
    };
    loadHoneypots();
  }, []);

  // Honeypot selection handler
  const handleSelectHoneypot = useCallback((honeypotId: string) => {
    setAttackers([]); // Clear previous attackers to prevent ghost nodes on Globe
    setSelectedHoneypotId(honeypotId);
  }, []);

  // Fetch attackers when honeypot selection changes (for persistent Globe nodes)
  useEffect(() => {
    const loadAttackers = async () => {
      try {
        const data = await fetchAllAttackers(selectedHoneypotId || undefined, 500, timeRange);
        setAttackers(data.attackers);
      } catch (err) {
        console.error('Failed to fetch attackers:', err);
      }
    };
    loadAttackers();

    // Refresh attackers periodically (every 30s) for new persistent nodes
    const interval = setInterval(loadAttackers, 30000);
    return () => clearInterval(interval);
  }, [selectedHoneypotId, timeRange]);

  // Calculate last attack time - Prioritize live events stream over polled status
  // Calculate last attack time - Prioritize truly recent time from either source
  const lastAttackTime = useMemo(() => {
    let eventTime: Date | null = null;
    let statusTime: Date | null = null;

    // 1. Get time from most recent event (real-time source)
    if (events.length > 0 && events[0].timestamp) {
      eventTime = new Date(events[0].timestamp);
    }

    // 2. Get time from status (polled source)
    if (status?.last_attack) {
      statusTime = new Date(status.last_attack);
    }

    // Return the more recent of the two
    if (eventTime && statusTime) {
      return eventTime > statusTime ? eventTime : statusTime;
    }

    return eventTime || statusTime;
  }, [events, status?.last_attack]);

  const activeProtocols = useMemo(
    () =>
      Array.from(
        new Set([
          ...(status?.ssh_enabled ? ['ssh'] : []),
          ...(status?.http_enabled ? ['http'] : []),
          ...(status?.agents?.filter((a) => a.status === 'running').map((a) => a.protocol) || []),
          ...Object.keys(stats?.protocol_breakdown || {}),
        ])
      ),
    [status, stats]
  );

  if (isLoading && !status) {
    return <div className="hp-loading">🕸️ Initializing ATLAS Systems...</div>;
  }

  return (
    <div className="hp-container">
      {/* Header */}
      <header className="hp-header">
        <div className="hp-header-left">
          <div className="hp-header-title-container">
            <h1>ATLAS</h1>
            <span className="hp-header-subtitle">
              Baselith<span className="hp-accent-sec">Sec</span>
              <span className="hp-dot">.</span>
            </span>
          </div>
          <div className="hp-tabs">
            {visibleTabs.map((tab) => (
              <button
                key={tab.id}
                className={`hp-tab ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <tab.icon size={14} />
                {tab.label}
              </button>
            ))}
          </div>
        </div>
        <div className="hp-header-right">
          <div className={`hp-status-badge ${status?.is_running ? 'active' : 'inactive'}`}>
            {status?.is_running ? <Wifi size={14} /> : <WifiOff size={14} />}
            {status?.is_running ? 'TRAPPING' : 'OFFLINE'}
          </div>
          {user && (
            <div className="hp-header-user">
              {user.roles && user.roles.length > 0 && (
                <span
                  className={`hp-role-badge ${user.roles.includes('admin') ? 'admin' : user.roles.includes('guest') ? 'guest' : 'user'}`}
                >
                  {user.roles.includes('admin')
                    ? 'ADMIN'
                    : user.roles.includes('guest')
                      ? 'GUEST'
                      : 'USER'}
                </span>
              )}
              <span className="hp-user-email">{user.username || maskEmail(user.email)}</span>
            </div>
          )}
          <button className="hp-header-logout" onClick={() => logout()} title="Logout">
            <LogOut size={16} />
          </button>
        </div>
      </header>

      {error && <div className="hp-error">⚠️ {error}</div>}

      {/* Tab Content */}
      {activeTab === 'monitor' && (
        <MonitorTab stats={stats} logs={logs} events={events} onSelectAttack={setSelectedAttack} />
      )}

      {activeTab === 'globe' && (
        <GlobeTab
          events={events}
          activeProtocols={activeProtocols}
          onSelectAttack={setSelectedAttack}
          honeypots={honeypots}
          selectedHoneypotId={selectedHoneypotId}
          onSelectHoneypot={handleSelectHoneypot}
          honeypotsLoading={honeypotsLoading}
          attackers={attackers}
          timeRange={timeRange}
          onTimeRangeChange={setTimeRange}
        />
      )}

      {activeTab === 'analytics' && <AnalyticsTab stats={stats} events={events} />}

      {activeTab === 'threats' && <ThreatsTab events={events} onSelectAttack={setSelectedAttack} />}

      {activeTab === 'pentest' && <PentestTab />}

      {activeTab === 'discovery' && <DiscoveryTab honeypotId={selectedHoneypotId} />}

      {activeTab === 'reports' && <ReportsTab />}

      {/* Attack Detail Modal */}
      {selectedAttack && (
        <AttackDetailModal event={selectedAttack} onClose={() => setSelectedAttack(null)} />
      )}

      {/* Dynamic System Footer */}
      <footer className="hp-footer">
        <div className="hp-footer-metrics">
          {/* System Status */}
          <div
            className={`hp-footer-metric ${status?.is_running ? 'hp-footer-metric--online' : 'hp-footer-metric--offline'}`}
          >
            <div className="hp-footer-metric-indicator" />
            <span className="hp-footer-metric-label">System</span>
            <span className="hp-footer-metric-value">
              {status?.is_running ? 'Online' : 'Offline'}
            </span>
          </div>

          {/* Active Honeypots */}
          <div className="hp-footer-metric">
            <span className="hp-footer-metric-label">ATLAS Nodes</span>
            <span className="hp-footer-metric-value hp-footer-metric-value--accent">
              {honeypots.filter((h) => h.enabled).length}
            </span>
            <span className="hp-footer-metric-sublabel">active</span>
          </div>

          {/* Total Events */}
          <div className="hp-footer-metric">
            <span className="hp-footer-metric-label">Total Events</span>
            <span className="hp-footer-metric-value hp-footer-metric-value--highlight">
              {stats?.total_events || events.length || 0}
            </span>
          </div>

          {/* Unique Attackers */}
          <div className="hp-footer-metric">
            <span className="hp-footer-metric-label">Attackers</span>
            <span className="hp-footer-metric-value">{stats?.unique_ips || 0}</span>
          </div>
        </div>

        <div className="hp-footer-last-attack">
          <span className="hp-footer-last-attack-label">Last attack:</span>
          <span className="hp-footer-last-attack-time">
            {lastAttackTime ? lastAttackTime.toLocaleString() : 'None'}
          </span>
        </div>
      </footer>
    </div>
  );
};

export default HoneypotPanel;
