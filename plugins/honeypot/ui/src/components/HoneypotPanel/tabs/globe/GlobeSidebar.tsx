/**
 * GlobeSidebar - Collapsible sidebar with honeypot selector
 */

import { ChevronLeft, ChevronRight, Zap, Tag } from 'lucide-react';
import type { HoneypotInfo } from '../../../types';
import { HoneypotSelector } from '../../../HoneypotSelector';

interface GlobeSidebarProps {
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
  honeypots: HoneypotInfo[];
  selectedHoneypot: HoneypotInfo | undefined;
  selectedId: string | null;
  onSelect: (honeypotId: string) => void;
  loading?: boolean;
}

export function GlobeSidebar({
  collapsed,
  setCollapsed,
  honeypots,
  selectedHoneypot,
  selectedId,
  onSelect,
  loading = false,
}: GlobeSidebarProps) {
  return (
    <div className={`hp-globe-sidebar ${collapsed ? 'hp-globe-sidebar--collapsed' : ''}`}>
      {/* Collapse Toggle Button */}
      <button
        className="hp-sidebar-toggle"
        onClick={() => setCollapsed(!collapsed)}
        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>

      {!collapsed && (
        <div className="hp-sidebar-scroll-wrapper">
          <HoneypotSelector
            honeypots={honeypots}
            selectedId={selectedId}
            onSelect={onSelect}
            loading={loading}
          />

          {/* Selected Honeypot Info with Tags */}
          {selectedHoneypot && (
            <div className="hp-selected-honeypot-info">
              <h4>{selectedHoneypot.name}</h4>
              <p>{selectedHoneypot.description}</p>

              {/* Tags Section */}
              {selectedHoneypot.tags && selectedHoneypot.tags.length > 0 && (
                <div className="hp-honeypot-tags">
                  <Tag size={12} />
                  {selectedHoneypot.tags.map((tag, idx) => (
                    <span key={idx} className="hp-honeypot-tag">
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              <div className="hp-honeypot-stats">
                <span>Port: {selectedHoneypot.port}</span>
                <span>Attackers: {selectedHoneypot.active_attackers}</span>
                <span>Events: {selectedHoneypot.total_events}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Collapsed state: show icon only */}
      {collapsed && selectedHoneypot && (
        <div className="hp-sidebar-collapsed-info" title={selectedHoneypot.name}>
          <Zap size={18} />
          <span className="hp-sidebar-collapsed-count">{honeypots.length}</span>
        </div>
      )}
    </div>
  );
}
