/**
 * NodeTooltip - Hover tooltip for attacker nodes
 */

import React from 'react';
import { NodeTooltipProps } from '../types';
import { getCountryFlag } from '../../geoUtils';
import { normalizeIpDisplay } from '../../api';

export const NodeTooltip: React.FC<NodeTooltipProps> = ({ node }) => {
  return (
    <div
      className="attack-node-tooltip"
      style={{
        left: `calc(50% + ${node.x}px)`,
        top: `calc(50% + ${node.y}px)`,
        bottom: 'auto',
        transform: 'translate(-50%, -170%)',
      }}
    >
      <span>{getCountryFlag(node?.country_code || '')}</span>
      <span>{node?.ip ? normalizeIpDisplay(node.ip) : 'Unknown'}</span>
      <span className="tooltip-protocol">{node?.protocol?.toUpperCase()}</span>
    </div>
  );
};
