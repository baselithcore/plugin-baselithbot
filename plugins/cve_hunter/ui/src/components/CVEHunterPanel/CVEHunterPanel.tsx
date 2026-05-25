/**
 * CVEHunterPanel - Main Dashboard Component
 *
 * Refactored to use modular hooks and tab components.
 */

import { useState, useCallback } from 'react';
import { Activity, Eye, Shield, Zap, LogOut } from 'lucide-react';
import { useAuth } from '../../../../../auth/ui/src';

import type { CVERecord } from '../types';
import type { AttackChain } from '../api';
import { fetchCVEDetail, triggerScan } from '../api';

import { useCVEHunterData, useCVECorrelator } from './hooks';
import { MonitorTab, AnalyticsTab, FeedTab } from './tabs';
import { TabType, CVEHunterPanelProps } from './types';

import CVEDetailModal from '../CVEDetailModal';
import AttackChainModal from '../AttackChainModal';

import './CVEHunterPanel.css';

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

const CVEHunterPanel = ({ onCVESelect }: CVEHunterPanelProps) => {
  // Tab state
  const [activeTab, setActiveTab] = useState<TabType>('monitor');
  const [selectedCVE, setSelectedCVE] = useState<CVERecord | null>(null);
  const [selectedChain, setSelectedChain] = useState<AttackChain | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [selectedAgentFilter, setSelectedAgentFilter] = useState<string | null>(null);

  const { logout, user } = useAuth();

  // Data hooks
  const {
    swarmStatus,
    cves,
    stats,
    discoveryLogs,
    findings,
    isLoading,
    error,
    agents,
    setDiscoveryLogs,
    setError,
    terminalRef,
    terminalEndRef,
    loadData,
  } = useCVEHunterData();

  const {
    attackChains,
    correlations,
    unifiedFindings,
    dastFindings,
    findingCorrelations,
    feedbackAudit,
    topDastFindings,
    topUnifiedFindings,
    filteredFeedback,
    recentFeedback,
    feedbackFilter,
    setFeedbackFilter,
    feedbackQuery,
    setFeedbackQuery,
    handleUnifiedFeedback,
    handleDastFeedback,
    handleCorrelationFeedback,
    handleClassicCorrelationFeedback,
  } = useCVECorrelator();

  // Modal handler
  const handleCVESelect = useCallback(
    (cve: CVERecord) => {
      setSelectedCVE(cve);
      onCVESelect?.(cve);
    },
    [onCVESelect]
  );

  const handleCVEClickById = useCallback(
    async (cveId: string) => {
      const found = cves.find((c) => c.cve_id === cveId);
      if (found) {
        handleCVESelect(found);
      } else {
        try {
          const detail = await fetchCVEDetail(cveId);
          handleCVESelect(detail);
        } catch (err) {
          console.error('Failed to fetch CVE detail:', err);
        }
      }
    },
    [cves, handleCVESelect]
  );

  const handleScan = useCallback(async () => {
    setIsScanning(true);
    setDiscoveryLogs((prev) => [
      ...prev,
      {
        timestamp: new Date().toISOString(),
        message: 'SCANNER: Manual scan trigger received. Initializing protocol...',
        is_alert: false,
        is_error: false,
      },
    ]);

    try {
      await triggerScan(7);
      await loadData();
    } catch (err) {
      setError('Scan failed');
    } finally {
      setIsScanning(false);
    }
  }, [setDiscoveryLogs, loadData, setError]);

  const handleAgentClick = useCallback((agentType: string) => {
    setSelectedAgentFilter((prev) => (prev === agentType ? null : agentType));
  }, []);

  const handleClearLogs = useCallback(() => {
    setDiscoveryLogs([]);
  }, [setDiscoveryLogs]);

  return (
    <div className="cve-hunter">
      {/* Detail Modal */}
      {selectedCVE && <CVEDetailModal cve={selectedCVE} onClose={() => setSelectedCVE(null)} />}
      {selectedChain && (
        <AttackChainModal
          chain={selectedChain}
          onClose={() => setSelectedChain(null)}
          onCveClick={(cveId) => {
            setSelectedChain(null);
            handleCVEClickById(cveId);
          }}
        />
      )}

      {/* Header */}
      <header className="cve-header">
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <h1>
            <Shield size={28} />
            CVE<span>_</span>HUNTER
          </h1>

          {/* Internal Tabs */}
          <div className="cve-tabs">
            <button
              className={`cve-tab-button ${activeTab === 'monitor' ? 'active' : ''}`}
              onClick={() => setActiveTab('monitor')}
            >
              <Activity size={14} /> Swarm Monitor
            </button>
            <button
              className={`cve-tab-button ${activeTab === 'analytics' ? 'active' : ''}`}
              onClick={() => setActiveTab('analytics')}
            >
              <Zap size={14} /> Analytics
            </button>
            <button
              className={`cve-tab-button ${activeTab === 'feed' ? 'active' : ''}`}
              onClick={() => setActiveTab('feed')}
            >
              <Eye size={14} /> CVE Feed
            </button>
          </div>
        </div>

        <div className="cve-header-right">
          <div className={`status-badge ${isScanning ? 'scanning' : ''}`}>
            <span className="pulse-dot" />
            {isScanning ? 'SCANNING' : 'MONITORING'}
          </div>

          {user && (
            <div className="cve-header-user">
              {user.roles && user.roles.length > 0 && (
                <span
                  className={`cve-role-badge ${user.roles.includes('admin') ? 'admin' : 'user'}`}
                >
                  {user.roles.includes('admin') ? 'ADMIN' : 'USER'}
                </span>
              )}
              <span className="cve-user-email">{user.username || maskEmail(user.email)}</span>
            </div>
          )}

          <button className="cve-header-logout" onClick={() => logout()} title="Logout">
            <LogOut size={16} />
          </button>
        </div>
      </header>

      {/* Tab Content */}
      {activeTab === 'monitor' && (
        <MonitorTab
          swarmStatus={swarmStatus}
          stats={stats}
          agents={agents}
          discoveryLogs={discoveryLogs}
          findings={findings}
          isScanning={isScanning}
          selectedAgentFilter={selectedAgentFilter}
          terminalRef={terminalRef}
          terminalEndRef={terminalEndRef}
          onAgentClick={handleAgentClick}
          onScan={handleScan}
          onClearLogs={handleClearLogs}
          setSelectedAgentFilter={setSelectedAgentFilter}
        />
      )}

      {activeTab === 'analytics' && (
        <AnalyticsTab
          swarmStatus={swarmStatus}
          stats={stats}
          cves={cves}
          findings={findings}
          attackChains={attackChains}
          correlations={correlations}
          unifiedFindings={unifiedFindings}
          dastFindings={dastFindings}
          findingCorrelations={findingCorrelations}
          feedbackAudit={feedbackAudit}
          discoveryLogs={discoveryLogs}
          topUnifiedFindings={topUnifiedFindings}
          topDastFindings={topDastFindings}
          filteredFeedback={filteredFeedback}
          recentFeedback={recentFeedback}
          feedbackFilter={feedbackFilter}
          setFeedbackFilter={setFeedbackFilter}
          feedbackQuery={feedbackQuery}
          setFeedbackQuery={setFeedbackQuery}
          isScanning={isScanning}
          onChainClick={setSelectedChain}
          onCVEClickById={handleCVEClickById}
          handleUnifiedFeedback={handleUnifiedFeedback}
          handleDastFeedback={handleDastFeedback}
          handleCorrelationFeedback={handleCorrelationFeedback}
          handleClassicCorrelationFeedback={handleClassicCorrelationFeedback}
          setDiscoveryLogs={setDiscoveryLogs}
          setError={setError}
        />
      )}

      {activeTab === 'feed' && (
        <FeedTab
          stats={stats}
          cves={cves}
          isLoading={isLoading}
          error={error}
          onCVESelect={handleCVESelect}
        />
      )}
    </div>
  );
};

export default CVEHunterPanel;
