/**
 * TargetSelector - Dropdown for selecting pentest target
 */

import React from 'react';
import { Server, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import type { PentestTarget } from '../../api';
import './PentestTab.css';

interface TargetSelectorProps {
  targets: PentestTarget[];
  selectedTargetId: string;
  onChange: (targetId: string) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export const TargetSelector: React.FC<TargetSelectorProps> = ({
  targets,
  selectedTargetId,
  onChange,
  isLoading,
  disabled = false,
}) => {
  const selectedTarget = targets.find((t) => t.agent_id === selectedTargetId);

  return (
    <div className="hp-target-selector">
      <label className="hp-target-label">
        <Server size={14} />
        Target Agent
      </label>
      <div className="hp-target-select-wrapper">
        {isLoading ? (
          <div className="hp-target-loading">
            <Loader2 size={14} className="spin" />
            Loading targets...
          </div>
        ) : (
          <select
            className="hp-target-select"
            value={selectedTargetId}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
          >
            {targets.map((target) => (
              <option key={target.agent_id} value={target.agent_id}>
                {target.name}
                {target.is_mock ? ' (Mock)' : ''}
                {!target.is_healthy ? ' ⚠️' : ''}
              </option>
            ))}
          </select>
        )}
        {selectedTarget && (
          <div className="hp-target-status">
            {selectedTarget.is_healthy ? (
              <CheckCircle size={14} className="hp-status-healthy" />
            ) : (
              <AlertCircle size={14} className="hp-status-unhealthy" />
            )}
          </div>
        )}
      </div>
      {selectedTarget?.description && (
        <p className="hp-target-description">{selectedTarget.description}</p>
      )}
    </div>
  );
};
