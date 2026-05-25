/**
 * GlobeTab - Geographic attack visualization with timeline
 *
 * REDESIGNED & MODULARIZED:
 * - ATTACK NETWORK GRAPH as the visual protagonist (80%+ of space)
 * - Collapsible sidebar with honeypot selector
 * - Bottom overlay for Recent Attack Origins (horizontal cards with scroll arrows)
 * - Professional card design with better visual hierarchy
 * - Modularized into smaller, focused components
 */

import { useState, useRef, useMemo } from 'react';
import { Activity } from 'lucide-react';
import type { GraphNode } from '../../types';
import type { GlobeTabProps, DisplayItem, FilterType } from './globe/types';
import * as api from '../../api';
import CrucixMapView from '../../CrucixMap';
import { GlobeSidebar } from './globe/GlobeSidebar';
import { GlobeFilters } from './globe/GlobeFilters';
import { AttackOriginCards } from './globe/AttackOriginCards';
import {
  getProtocolColor,
  calculateCutoffTime,
  getSuggestions as getSearchSuggestions,
  createSyntheticEvent,
} from './globe/utils';

export function GlobeTab({
  events,
  activeProtocols,
  onSelectAttack,
  honeypots,
  selectedHoneypotId,
  onSelectHoneypot,
  honeypotsLoading = false,
  attackers = [],
  isActive = true,
  timeRange,
  onTimeRangeChange,
}: GlobeTabProps) {
  // State
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<FilterType>('all');
  const [showSuggestions, setShowSuggestions] = useState(false);

  // Refs
  const cardsContainerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Filter Events and Attackers
  const { filteredEvents, filteredAttackers } = useMemo(() => {
    const cutoffTime = calculateCutoffTime(timeRange);

    const fEvents = events.filter((e) => {
      // Time Filter
      if (cutoffTime) {
        const eventTime = new Date(e.timestamp);
        if (eventTime < cutoffTime) return false;
      }

      // Honeypot Filter
      if (selectedHoneypotId && e.honeypot_id !== selectedHoneypotId) return false;
      // Protocol Filter
      if (activeProtocols.length > 0 && !activeProtocols.includes(e.protocol)) return false;
      // Type Filter
      if (filterType === 'human' && e.is_bot) return false;
      if (filterType === 'bot' && !e.is_bot) return false;
      // Search Filter
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        return (
          e.source_ip.toLowerCase().includes(term) ||
          e.geo?.country?.toLowerCase().includes(term) ||
          e.geo?.city?.toLowerCase().includes(term)
        );
      }

      return true;
    });

    const fAttackers = attackers.filter((a) => {
      // Time Filter
      if (cutoffTime) {
        const attackerTime = new Date(a.last_seen);
        if (attackerTime < cutoffTime) return false;
      }

      // Protocol Filter
      if (activeProtocols.length > 0) {
        const hasActiveProtocol = a.protocols.some((p) => activeProtocols.includes(p));
        if (!hasActiveProtocol) return false;
      }

      // Search Filter
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        return (
          a.ip.toLowerCase().includes(term) ||
          a.country?.toLowerCase().includes(term) ||
          a.city?.toLowerCase().includes(term)
        );
      }

      // Type Filter
      if (filterType === 'human' && a.is_bot) return false;
      if (filterType === 'bot' && !a.is_bot) return false;

      return true;
    });

    return { filteredEvents: fEvents, filteredAttackers: fAttackers };
  }, [events, attackers, searchTerm, activeProtocols, filterType, selectedHoneypotId, timeRange]);

  // Prepare Display Items for Cards
  const displayItems: DisplayItem[] = useMemo(() => {
    const itemsMap = new Map<string, DisplayItem>();

    // 1. Start with Persistent Attackers
    filteredAttackers.forEach((a) => {
      itemsMap.set(a.ip, {
        type: 'attacker',
        data: a,
        id: a.ip,
        ip: a.ip,
        country: a.country || 'Unknown',
        city: a.city || '',
        protocol: a.protocols[0] || 'bgp',
        severity: a.max_severity,
        timestamp: a.last_seen,
        is_bot: a.is_bot || false,
        confidence: 0,
      });
    });

    // 2. Overlay Live Events
    filteredEvents.forEach((e) => {
      const existing = itemsMap.get(e.source_ip);

      if (!existing || new Date(e.timestamp) > new Date(existing.timestamp)) {
        itemsMap.set(e.source_ip, {
          type: 'event',
          data: e,
          id: e.event_id,
          ip: e.source_ip,
          country: e.geo?.country || existing?.country || 'Unknown',
          city: e.geo?.city || existing?.city || '',
          protocol: e.protocol,
          severity: e.severity,
          timestamp: e.timestamp,
          is_bot: e.is_bot || false,
          confidence: e.bot_confidence || 0,
        });
      }
    });

    // Convert to array and Sort by Time (Newest First)
    return Array.from(itemsMap.values()).sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }, [filteredAttackers, filteredEvents]);

  // Autocomplete Suggestions
  const suggestions = getSearchSuggestions(searchTerm, events);

  const handleSuggestionClick = (value: string) => {
    setSearchTerm(value);
    setShowSuggestions(false);
  };

  // Get selected honeypot info
  const selectedHoneypot = honeypots.find((h) => h.id === selectedHoneypotId);
  const protocolColor = selectedHoneypot ? getProtocolColor(selectedHoneypot.protocol) : '#00ffff';

  // Handler for Map Node Selection
  const handleNodeSelect = async (node: GraphNode) => {
    if (node.type !== 'attacker' || !node.ip) return;

    // Attempt to fetch latest real event for this IP
    try {
      const eventData = await api.fetchEvents(1, 1, { source_ip: node.ip });
      if (eventData.items && eventData.items.length > 0) {
        onSelectAttack(eventData.items[0]);
        return;
      }
    } catch (e) {
      console.error('Failed to fetch real event for node:', e);
    }

    // Fallback to synthetic event
    const synthEvent = createSyntheticEvent(node, 'node');
    onSelectAttack(synthEvent);
  };

  // Scroll handlers for attack origins
  const scrollCards = (direction: 'left' | 'right') => {
    if (cardsContainerRef.current) {
      const scrollAmount = 200;
      const newScrollLeft =
        cardsContainerRef.current.scrollLeft +
        (direction === 'right' ? scrollAmount : -scrollAmount);
      cardsContainerRef.current.scrollTo({
        left: newScrollLeft,
        behavior: 'smooth',
      });
    }
  };

  return (
    <div className={`hp-globe ${sidebarCollapsed ? 'hp-globe--sidebar-collapsed' : ''}`}>
      {/* Collapsible Sidebar */}
      <GlobeSidebar
        collapsed={sidebarCollapsed}
        setCollapsed={setSidebarCollapsed}
        honeypots={honeypots}
        selectedHoneypot={selectedHoneypot}
        selectedId={selectedHoneypotId}
        onSelect={onSelectHoneypot}
        loading={honeypotsLoading}
      />

      {/* Main Visualization Container */}
      <div className="hp-globe-main-container">
        <CrucixMapView
          key={selectedHoneypotId || 'global'}
          activeProtocols={activeProtocols}
          events={filteredEvents}
          attackers={filteredAttackers}
          honeypotContext={selectedHoneypot}
          onSelectNode={handleNodeSelect}
          isActive={isActive}
        />

        {/* Recent Attack Origins - Bottom Overlay */}
        <div className="hp-attack-origins-overlay">
          <div className="hp-origins-header">
            <div className="hp-origins-title-group">
              <Activity size={14} />
              <span>Attack Origins</span>
              {selectedHoneypot && (
                <span
                  className="hp-origins-honeypot-tag"
                  style={{
                    color: protocolColor,
                    border: `1px solid ${protocolColor}40`,
                    background: `${protocolColor}15`,
                  }}
                >
                  {selectedHoneypot.name}
                </span>
              )}
            </div>

            <GlobeFilters
              searchTerm={searchTerm}
              setSearchTerm={setSearchTerm}
              filterType={filterType}
              setFilterType={setFilterType}
              timeRange={timeRange}
              onTimeRangeChange={onTimeRangeChange}
              searchInputRef={searchInputRef}
              filteredCount={displayItems.length}
              suggestions={suggestions}
              showSuggestions={showSuggestions}
              onSuggestionClick={handleSuggestionClick}
            />
          </div>

          <AttackOriginCards
            items={displayItems}
            onSelectAttack={onSelectAttack}
            cardsContainerRef={cardsContainerRef}
            scrollCards={scrollCards}
            selectedHoneypotId={selectedHoneypotId}
          />
        </div>
      </div>
    </div>
  );
}
