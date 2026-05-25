import { CLUSTER_COLORS } from '../constants/graphConstants';
import { getCountryFlag } from '../utils/graphHelpers';
import type { DiscoveryGraphNode } from '../../../../types';

interface NodeTooltipProps {
  node: DiscoveryGraphNode;
  isLocked: boolean;
  onViewDetails: () => void;
}

export function NodeTooltip({ node, isLocked, onViewDetails }: NodeTooltipProps) {
  return (
    <div className={`graph-hover-tooltip ${isLocked ? 'is-locked' : ''}`}>
      <div className="tooltip-header">
        <span className="tooltip-ip">{node.id}</span>
        {node.is_hub &&
          (node.is_confirmed_cc ? (
            <span className="hub-badge">C&C</span>
          ) : (
            <span className="potential-cc-badge">Potential C&C</span>
          ))}
      </div>
      <div className="tooltip-body">
        <div className="tooltip-row">
          <span className="tooltip-label">Type</span>
          <span className="tooltip-value">{node.type}</span>
        </div>
        {node.country && (
          <div className="tooltip-row">
            <span className="tooltip-label">Location</span>
            <span className="tooltip-value">
              {node.country_code && (
                <span className="country-flag">{getCountryFlag(node.country_code)}</span>
              )}
              {node.country}
            </span>
          </div>
        )}
        <div className="tooltip-row">
          <span className="tooltip-label">Attacks</span>
          <span className="tooltip-value highlight">{node.attack_count.toLocaleString()}</span>
        </div>
        <div className="tooltip-row">
          <span className="tooltip-label">Connections</span>
          <span className="tooltip-value">{node.degree}</span>
        </div>
        {node.cluster_id && (
          <div className="tooltip-row">
            <span className="tooltip-label">Cluster</span>
            <span className="tooltip-value">
              <span
                className="cluster-indicator"
                style={{
                  backgroundColor:
                    CLUSTER_COLORS[parseInt(node.cluster_id) % CLUSTER_COLORS.length],
                }}
              />
              #{node.cluster_id}
            </span>
          </div>
        )}
      </div>

      {isLocked ? (
        <div className="tooltip-footer-actions">
          <button className="view-details-btn" onClick={onViewDetails}>
            View Full Details
          </button>
        </div>
      ) : (
        <div className="tooltip-footer">Click to lock details</div>
      )}
    </div>
  );
}
