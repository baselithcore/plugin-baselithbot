/**
 * HoneypotSelector - Modern card-based honeypot selector
 *
 * Premium UI with:
 * - Card-based layout with hover effects
 * - Live status indicators
 * - Smooth micro-animations
 * - Better visual hierarchy
 */

import { useState } from 'react';
import {
  Shield,
  Terminal,
  Globe,
  Tag,
  Activity,
  AlertTriangle,
  Zap,
  ChevronDown,
  ChevronUp,
  Server,
} from 'lucide-react';
import type { HoneypotInfo } from './types';
import './HoneypotSelector.css';

interface HoneypotSelectorProps {
  honeypots: HoneypotInfo[];
  selectedId: string | null;
  onSelect: (honeypotId: string) => void;
  loading?: boolean;
}

const getProtocolIcon = (protocol: string) => {
  switch (protocol) {
    case 'ssh':
      return <Terminal size={18} />;
    case 'http':
      return <Globe size={18} />;
    default:
      return <Server size={18} />;
  }
};

const getProtocolColor = (protocol: string) => {
  switch (protocol) {
    case 'ssh':
      return '#ff4757';
    case 'http':
      return '#00d2d3';
    default:
      return '#9d4edd';
  }
};

export function HoneypotSelector({
  honeypots,
  selectedId,
  onSelect,
  loading = false,
}: HoneypotSelectorProps) {
  const [collapsed, setCollapsed] = useState(false);

  if (loading) {
    return (
      <div className="hp-selector">
        <div className="hp-selector__header">
          <Shield size={18} />
          <span>Select ATLAS</span>
        </div>
        <div className="hp-selector__loading">
          <div className="hp-selector__loading-spinner" />
          <span>Loading ATLAS...</span>
        </div>
      </div>
    );
  }

  if (honeypots.length === 0) {
    return (
      <div className="hp-selector">
        <div className="hp-selector__header">
          <Shield size={18} />
          <span>Select ATLAS</span>
        </div>
        <div className="hp-selector__empty">
          <AlertTriangle size={24} />
          <span>No ATLAS configured</span>
        </div>
      </div>
    );
  }

  return (
    <div className="hp-selector">
      <div
        className="hp-selector__header"
        onClick={() => setCollapsed(!collapsed)}
        role="button"
        tabIndex={0}
      >
        <div className="hp-selector__header-left">
          <Shield size={18} />
          <span>Select ATLAS</span>
        </div>
        <div className="hp-selector__header-right">
          <span className="hp-selector__count">{honeypots.length} available</span>
          {collapsed ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
        </div>
      </div>

      {!collapsed && (
        <div className="hp-selector__list">
          {honeypots.map((honeypot) => {
            const isSelected = selectedId === honeypot.id;
            const isDisabled = !honeypot.enabled;
            const protocolColor = getProtocolColor(honeypot.protocol);

            return (
              <div
                key={honeypot.id}
                className={`hp-selector__card ${isSelected ? 'hp-selector__card--selected' : ''} ${
                  isDisabled ? 'hp-selector__card--disabled' : ''
                }`}
                onClick={() => !isDisabled && onSelect(honeypot.id)}
                style={{ '--protocol-color': protocolColor } as React.CSSProperties}
              >
                {/* Main Content Area */}
                <div className="hp-selector__main">
                  {/* Icon Container */}
                  <div
                    className="hp-selector__icon-wrapper"
                    style={{
                      background: isSelected ? protocolColor : `${protocolColor}15`,
                      color: isSelected ? '#fff' : protocolColor,
                      boxShadow: isSelected ? `0 0 15px ${protocolColor}60` : 'none',
                    }}
                  >
                    {getProtocolIcon(honeypot.protocol)}
                  </div>

                  {/* Info Block */}
                  <div className="hp-selector__info">
                    <div className="hp-selector__name-row">
                      <span className="hp-selector__name">{honeypot.name}</span>
                      {honeypot.enabled && <div className="hp-selector__live-dot" title="Online" />}
                    </div>

                    <div className="hp-selector__meta-badges">
                      <span className="hp-selector__badge hp-selector__badge--protocol">
                        {honeypot.protocol}
                      </span>
                      <span className="hp-selector__badge hp-selector__badge--port">
                        :{honeypot.port}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Footer Stats */}
                <div className="hp-selector__footer">
                  <div className="hp-selector__footer-stats">
                    <div className="hp-selector__stat" title="Active Attackers">
                      <Activity size={12} />
                      <span className="hp-selector__stat-value">{honeypot.active_attackers}</span>
                    </div>
                    <div className="hp-selector__stat" title="Total Events">
                      <Zap size={12} />
                      <span className="hp-selector__stat-value">{honeypot.total_events}</span>
                    </div>
                  </div>

                  {honeypot.tags.length > 0 && (
                    <div className="hp-selector__tags-pill" title={honeypot.tags.join(', ')}>
                      <Tag size={10} />
                      <span>{honeypot.tags.length}</span>
                    </div>
                  )}
                </div>

                {/* Selection Glow (handled by CSS, mainly) */}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default HoneypotSelector;
