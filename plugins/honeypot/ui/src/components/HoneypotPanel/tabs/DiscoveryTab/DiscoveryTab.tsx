import { useState } from 'react';
import {
  Users,
  Bug,
  Activity,
  AlertTriangle,
  LayoutGrid,
  Network,
  Lightbulb,
  Globe,
} from 'lucide-react';

import { useDiscoveryAnalysis } from './hooks/useDiscoveryAnalysis';
import { DiscoveryHeader } from './components/DiscoveryHeader';
import { DiscoverySummary } from './components/DiscoverySummary';
import { BotnetsCCTab } from './components/BotnetsCCTab';
import { DiscoveryGraph } from './components/DiscoveryGraph';
import { ZeroDaySection } from './components/ZeroDaySection';
import { SuggestionsSection } from './components/SuggestionsSection';
import { RDNSPanel } from './components/RDNSPanel';
import { EmptyState } from './components/EmptyState';
import { filterAnomalies, getCounts } from './utils';

import './DiscoveryTab.css';

interface DiscoveryTabProps {
  honeypotId?: string | null;
}

export function DiscoveryTab({ honeypotId }: DiscoveryTabProps) {
  const { loading, analyzing, result, error, runAnalysis } = useDiscoveryAnalysis(honeypotId);
  const [activeSection, setActiveSection] = useState<
    'botnets' | 'zeroday' | 'suggestions' | 'rdns'
  >('botnets');
  const [viewMode, setViewMode] = useState<'list' | 'graph'>('list');

  // Filters
  const zerodayAnomalies = filterAnomalies(result, ['zeroday', 'novel']);
  const exploitAnomalies = filterAnomalies(result, ['exploit', 'attack_chain']);
  const networkAnomalies =
    result?.anomalies.filter(
      (a) =>
        !['zeroday', 'novel', 'exploit', 'attack_chain', 'threat_intel', 'intel'].some((t) =>
          a.anomaly_type.includes(t)
        )
    ) || [];

  // Counts
  const { zerodayCount, exploitCount } = getCounts(result, zerodayAnomalies, exploitAnomalies);

  // Suggestion count
  const suggestionsCount = (result?.suggestions || []).filter(
    (s) => !s.dismissed && !s.applied
  ).length;

  return (
    <div className="discovery-tab">
      <DiscoveryHeader result={result} analyzing={analyzing} onRunAnalysis={() => runAnalysis()} />

      {error && (
        <div className="discovery-error">
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      {loading && !result ? (
        <div className="discovery-loading">
          <Activity size={24} className="spinning" />
          <span>Analyzing attack patterns...</span>
        </div>
      ) : result ? (
        <>
          <DiscoverySummary
            result={result}
            zerodayCount={zerodayCount}
            exploitCount={exploitCount}
          />

          {/* Section Tabs */}
          <div className="discovery-section-controls">
            <div className="discovery-section-tabs">
              <button
                className={`discovery-section-tab ${activeSection === 'botnets' ? 'active' : ''}`}
                onClick={() => setActiveSection('botnets')}
              >
                <Users size={14} />
                Botnets & C&C
              </button>
              <button
                className={`discovery-section-tab ${activeSection === 'zeroday' ? 'active' : ''}`}
                onClick={() => setActiveSection('zeroday')}
              >
                <Bug size={14} />
                Zero-Day & Exploits
                {(zerodayCount > 0 || exploitCount > 0) && (
                  <span className="tab-badge">{zerodayCount + exploitCount}</span>
                )}
              </button>
              <button
                className={`discovery-section-tab ${activeSection === 'suggestions' ? 'active' : ''}`}
                onClick={() => setActiveSection('suggestions')}
              >
                <Lightbulb size={14} />
                Suggestions
                {suggestionsCount > 0 && (
                  <span className="tab-badge suggestions-badge">{suggestionsCount}</span>
                )}
              </button>
              <button
                className={`discovery-section-tab ${activeSection === 'rdns' ? 'active' : ''}`}
                onClick={() => setActiveSection('rdns')}
              >
                <Globe size={14} />
                RDNS Intel
              </button>
            </div>

            {/* View Mode Toggle (Only for Botnets) */}
            {activeSection === 'botnets' && (
              <div className="discovery-view-toggle">
                <button
                  className={`view-toggle-btn ${viewMode === 'list' ? 'active' : ''}`}
                  onClick={() => setViewMode('list')}
                  title="List View"
                >
                  <LayoutGrid size={14} />
                </button>
                <button
                  className={`view-toggle-btn ${viewMode === 'graph' ? 'active' : ''}`}
                  onClick={() => setViewMode('graph')}
                  title="Graph View"
                >
                  <Network size={14} />
                </button>
              </div>
            )}
          </div>

          {/* Section Content */}
          <div className="discovery-content">
            {activeSection === 'botnets' &&
              (viewMode === 'list' ? (
                <BotnetsCCTab result={result} />
              ) : (
                <DiscoveryGraph result={result} />
              ))}
            {activeSection === 'zeroday' && (
              <ZeroDaySection
                zerodayAnomalies={zerodayAnomalies}
                exploitAnomalies={exploitAnomalies}
                networkAnomalies={networkAnomalies}
                zerodayCount={zerodayCount}
                exploitCount={exploitCount}
              />
            )}
            {activeSection === 'suggestions' && <SuggestionsSection result={result} />}
            {activeSection === 'rdns' && <RDNSPanel honeypotId={honeypotId} />}
          </div>
        </>
      ) : (
        <EmptyState onRunAnalysis={() => runAnalysis()} />
      )}
    </div>
  );
}
