/**
 * NodeDetailModal - Sleek popover for attacker node details
 *
 * Professional design with clean styling, positioned near the node.
 */

import { forwardRef, useMemo, useEffect } from 'react';
import { X, ExternalLink } from 'lucide-react';
import { NodeDetailModalProps } from '../types';
import { severityColors } from '../constants';
import { getCountryFlag, getCountryName } from '../../geoUtils';
import { normalizeIpDisplay } from '../../api';

export const NodeDetailModal = forwardRef<HTMLDivElement, NodeDetailModalProps>(
  ({ node, nodePosition, containerDimensions, onClose, onViewDetails }, ref) => {
    // Calculate smart position near the node
    const modalStyle = useMemo(() => {
      if (!nodePosition || !containerDimensions) {
        return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' };
      }

      const modalWidth = 220;
      const modalHeight = 180;
      const padding = 16;
      const offset = 50;

      let left = nodePosition.x + offset;
      let top = nodePosition.y - modalHeight / 2;

      // Boundary checks
      if (left + modalWidth + padding > containerDimensions.width) {
        left = nodePosition.x - modalWidth - offset;
      }
      if (left < padding) left = padding;
      if (top < padding) top = padding;
      if (top + modalHeight + padding > containerDimensions.height) {
        top = containerDimensions.height - modalHeight - padding;
      }

      return { top: `${top}px`, left: `${left}px`, transform: 'none' };
    }, [nodePosition, containerDimensions]);

    const severityColor = severityColors[node?.severity || 'info'];

    // Close on Escape key
    useEffect(() => {
      const handleEscape = (e: KeyboardEvent) => {
        if (e.key === 'Escape') onClose();
      };
      window.addEventListener('keydown', handleEscape);
      return () => window.removeEventListener('keydown', handleEscape);
    }, [onClose]);

    return (
      <div
        ref={ref}
        className="node-detail-popover"
        style={modalStyle}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="popover-header">
          <span className="popover-flag">{getCountryFlag(node?.country_code || '')}</span>
          <div className="popover-title">
            <span className="popover-ip">{node?.ip ? normalizeIpDisplay(node.ip) : 'Unknown'}</span>
            <span className="popover-location">{getCountryName(node?.country_code || '')}</span>
          </div>
          <button className="popover-close" onClick={onClose} aria-label="Close">
            <X size={14} />
          </button>
        </div>

        {/* Stats */}
        <div className="popover-stats">
          <div className="popover-stat">
            <span className="stat-label">Protocol</span>
            <span className={`stat-badge protocol-${node?.protocol?.toLowerCase()}`}>
              {node?.protocol?.toUpperCase()}
            </span>
          </div>
          <div className="popover-stat">
            <span className="stat-label">Severity</span>
            <span
              className="stat-badge"
              style={{ background: severityColor + '25', color: severityColor }}
            >
              {node?.severity?.toUpperCase()}
            </span>
          </div>
          <div className="popover-stat">
            <span className="stat-label">Attacks</span>
            <span className="stat-value">{node?.attackCount || 1}</span>
          </div>
        </div>

        {/* Actions */}
        <div className="popover-actions" style={{ marginTop: '12px' }}>
          <button
            className="popover-btn"
            onClick={() => onViewDetails?.(node)}
            style={{
              width: '100%',
              padding: '8px 0',
              background: 'transparent',
              border: '1px solid rgba(0, 210, 211, 0.3)',
              borderRadius: '4px',
              color: '#00d2d3',
              fontSize: '11px',
              fontWeight: 600,
              letterSpacing: '0.5px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              transition: 'all 0.2s ease',
              textTransform: 'uppercase',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(0, 210, 211, 0.1)';
              e.currentTarget.style.borderColor = '#00d2d3';
              e.currentTarget.style.boxShadow = '0 0 8px rgba(0, 210, 211, 0.2)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.borderColor = 'rgba(0, 210, 211, 0.3)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            <ExternalLink size={12} strokeWidth={2.5} />
            <span>Analyze Threat</span>
          </button>
        </div>
      </div>
    );
  }
);

NodeDetailModal.displayName = 'NodeDetailModal';
