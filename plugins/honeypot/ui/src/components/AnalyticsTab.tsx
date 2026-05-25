/**
 * AnalyticsTab - Professional Analytics Dashboard Component
 * Features animated donut charts, KPI cards, attack trends, and CVE insights
 */

import { useState, useMemo, useEffect } from 'react';
import { fetchStats, fetchHoneypots, fetchCVEDetail } from './api';
import type { HoneypotStats, AttackEvent, CVERecord, HoneypotInfo } from './types';
import CVEDetailModal from './CVEDetailModal';
import CVECorrelationsPanel from './CVECorrelationsPanel';
import { calculateThreatScore, getCategoryIcon, getCategoryColor } from '../utils/analyticsHelpers';

// Modularized components
import { HoneypotFilter } from './AnalyticsTab/components/HoneypotFilter';
import { KPIRow } from './AnalyticsTab/components/KPIRow';
import { ChartsRow } from './AnalyticsTab/components/ChartsRow';
import { ActivityTimeline } from './AnalyticsTab/components/ActivityTimeline';
import { AttackCategoriesSection } from './AnalyticsTab/components/AttackCategoriesSection';
import { AttackersSection } from './AnalyticsTab/components/AttackersSection';
import { CVEInsightsSection } from './AnalyticsTab/components/CVEInsightsSection';

import './AnalyticsTab.css';

interface AnalyticsTabProps {
  stats: HoneypotStats | null;
  events: AttackEvent[];
  onFilterChange?: (honeypotId: string | null) => void;
}

const AnalyticsTab: React.FC<AnalyticsTabProps> = ({
  stats: initialStats,
  events,
  onFilterChange,
}) => {
  const [stats, setStats] = useState<HoneypotStats | null>(initialStats);
  const [selectedHoneypot, setSelectedHoneypot] = useState<string>('all');
  const [honeypots, setHoneypots] = useState<HoneypotInfo[]>([]);
  const [selectedCVE, setSelectedCVE] = useState<string | null>(null);
  const [showCVEPanel, setShowCVEPanel] = useState(false);

  // Load honeypots list
  useEffect(() => {
    fetchHoneypots().then(setHoneypots).catch(console.error);
  }, []);

  // Update stats when input stats change (only if showing global stats)
  useEffect(() => {
    if (selectedHoneypot === 'all') {
      setStats(initialStats);
    }
  }, [initialStats, selectedHoneypot]);

  // Handle filter change
  const handleFilterChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const hpId = e.target.value;
    setSelectedHoneypot(hpId);

    if (onFilterChange) {
      onFilterChange(hpId === 'all' ? null : hpId);
    }

    try {
      const newStats = await fetchStats(hpId === 'all' ? undefined : hpId);
      setStats(newStats);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  const handleCVEClick = (e: React.MouseEvent, cve: string) => {
    e.preventDefault();
    setSelectedCVE(cve);
  };

  const handleCloseModal = () => {
    setSelectedCVE(null);
  };

  const [cveRecord, setCveRecord] = useState<CVERecord | null>(null);

  useEffect(() => {
    if (!selectedCVE) {
      setCveRecord(null);
      return;
    }

    setCveRecord({
      cve_id: selectedCVE,
      title: `Vulnerability ${selectedCVE}`,
      description: 'Loading details...',
      severity: 'medium',
      cvss: null,
      source: 'nvd',
      published_date: null,
      last_modified: null,
      affected_products: [],
      references: [],
      cwe_ids: [],
      exploit_available: false,
      patch_available: false,
      ai_summary: null,
    });

    fetchCVEDetail(selectedCVE)
      .then(setCveRecord)
      .catch((err) => {
        console.error('Failed to fetch CVE details:', err);
        setCveRecord((prev) =>
          prev
            ? {
                ...prev,
                description: 'Failed to load details. Please try again later.',
              }
            : null
        );
      });
  }, [selectedCVE]);

  // Protocol chart data
  const protocolData = useMemo(() => {
    const colors: Record<string, string> = {
      ssh: '#ff4757',
      http: '#ff9f43',
      tcp: '#feca57',
      ftp: '#00d2d3',
      telnet: '#54a0ff',
    };
    return Object.entries(stats?.protocol_breakdown || {}).map(([protocol, count]) => ({
      label: protocol.toUpperCase(),
      value: count,
      color: colors[protocol.toLowerCase()] || '#8395a7',
    }));
  }, [stats?.protocol_breakdown]);

  // Severity chart data
  const severityData = useMemo(
    () => [
      { label: 'Critical', value: stats?.severity_breakdown?.critical || 0, color: '#ff3366' },
      { label: 'High', value: stats?.severity_breakdown?.high || 0, color: '#ff6b35' },
      { label: 'Medium', value: stats?.severity_breakdown?.medium || 0, color: '#ffbe0b' },
      { label: 'Low', value: stats?.severity_breakdown?.low || 0, color: '#00b4d8' },
      { label: 'Info', value: stats?.severity_breakdown?.info || 0, color: '#45aaf2' },
    ],
    [stats?.severity_breakdown]
  );

  // Bot chart data
  const botData = useMemo(
    () => [
      { label: 'Bots', value: stats?.bot_breakdown?.bot || 0, color: '#ff4757' },
      { label: 'Humans', value: stats?.bot_breakdown?.human || 0, color: '#2ed573' },
      { label: 'Unknown', value: stats?.bot_breakdown?.unknown || 0, color: '#747d8c' },
    ],
    [stats?.bot_breakdown]
  );

  // Threat score calculation
  const threatScore = useMemo(
    () => calculateThreatScore(stats?.severity_breakdown),
    [stats?.severity_breakdown]
  );

  // Category data sorted
  const categoryData = useMemo(() => {
    return Object.entries(stats?.category_breakdown || {})
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([category, count]) => ({
        category,
        count,
        percentage: (count / (stats?.total_events || 1)) * 100,
        icon: getCategoryIcon(category),
        color: getCategoryColor(category),
      }));
  }, [stats?.category_breakdown, stats?.total_events]);

  // Time stats
  const timeStats = useMemo(() => {
    const lastHour = stats?.events_last_hour || 0;
    const today = stats?.events_today || 0;
    const week = stats?.events_this_week || 0;
    return { lastHour, today, week };
  }, [stats?.events_last_hour, stats?.events_today, stats?.events_this_week]);

  // Unique countries count from events
  const uniqueCountries = useMemo(() => {
    const countries = new Set<string>();
    events.forEach((e) => {
      if (selectedHoneypot !== 'all' && e.honeypot_id !== selectedHoneypot) return;
      if (e.geo?.country_code) countries.add(e.geo.country_code);
    });
    return countries.size;
  }, [events, selectedHoneypot]);

  return (
    <div className="analytics-container">
      {/* Filters Toolbar */}
      <HoneypotFilter
        selectedHoneypot={selectedHoneypot}
        honeypots={honeypots}
        onFilterChange={handleFilterChange}
      />

      {/* KPI Summary Row */}
      <KPIRow
        totalEvents={stats?.total_events || 0}
        uniqueIps={stats?.unique_ips || 0}
        uniqueCountries={uniqueCountries}
        cveCorrelations={stats?.cve_correlations || 0}
        topMatchedCves={stats?.top_matched_cves?.length || 0}
        threatScore={threatScore}
        timeStats={timeStats}
      />

      {/* Charts Row */}
      <ChartsRow protocolData={protocolData} botData={botData} severityData={severityData} />

      {/* Activity Timeline */}
      <ActivityTimeline activityHistory={stats?.activity_history || []} />

      {/* Bottom Section: Categories + Attackers + CVEs */}
      <div className="analytics-bottom-grid">
        {/* Attack Categories */}
        <AttackCategoriesSection categoryData={categoryData} />

        {/* Top Attackers */}
        <AttackersSection topAttackerIps={stats?.top_attacker_ips || []} />

        {/* CVE Insights */}
        <CVEInsightsSection
          cveCorrelations={stats?.cve_correlations || 0}
          topMatchedCves={stats?.top_matched_cves || []}
          onCVEClick={handleCVEClick}
          onViewDetails={() => setShowCVEPanel(true)}
        />
      </div>

      {/* CVE Detail Modal */}
      {selectedCVE && cveRecord && <CVEDetailModal cve={cveRecord} onClose={handleCloseModal} />}

      {/* CVE Correlations Panel */}
      {showCVEPanel && <CVECorrelationsPanel onClose={() => setShowCVEPanel(false)} />}
    </div>
  );
};

export default AnalyticsTab;
