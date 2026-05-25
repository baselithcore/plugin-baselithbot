/**
 * GeoMapLegend - Severity color legend
 */

import React from 'react';
import { GeoMapLegendProps } from '../types';
import { severityColors } from '../constants';

export const GeoMapLegend: React.FC<GeoMapLegendProps> = () => {
  return (
    <div className="geo-map-legend">
      <div className="legend-title">Severity</div>
      {Object.entries(severityColors).map(([key, color]) => (
        <div key={key} className="legend-item">
          <span className="legend-dot" style={{ background: color }} />
          <span className="legend-label">{key.charAt(0).toUpperCase() + key.slice(1)}</span>
        </div>
      ))}
    </div>
  );
};
