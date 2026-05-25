/**
 * GeoMapHeader - Header stats overlay component
 */

import React from 'react';
import {
  Globe,
  Zap,
  Activity,
  Shield,
  AlertTriangle,
  Camera,
  Loader2,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { GeoMapHeaderProps } from '../types';
import { getThreatLevelLabel, formatAttackCount } from '../../geoUtils';

export const GeoMapHeader: React.FC<GeoMapHeaderProps> = ({
  stats,
  isConnected,
  threatLevel,
  attackVelocity,
  onRedistribute,
  onCapture,
  isCapturing = false,
  isFullscreen = false,
  onToggleFullscreen,
}) => {
  return (
    <div className="geo-map-header">
      <div className="geo-map-title">
        <Globe size={16} className="text-cyan-400" />
        <span className="text-sm font-bold tracking-wider">ATTACK NETWORK GRAPH</span>
        {isConnected ? (
          <span className="geo-map-status connected">
            <Zap size={10} fill="currentColor" /> LIVE
          </span>
        ) : (
          <span className="geo-map-status disconnected">
            <Activity size={10} /> OFFLINE
          </span>
        )}

        {/* Redistribution Button */}
        {onRedistribute && (
          <button
            onClick={onRedistribute}
            className="geo-map-action-btn"
            title="Redistribute Nodes"
          >
            <Globe size={12} />
            <span>RESET VIEW</span>
          </button>
        )}

        {/* Screenshot Capture Button */}
        {onCapture && (
          <button
            onClick={onCapture}
            className={`geo-map-action-btn geo-map-capture-btn ${isCapturing ? 'capturing' : ''}`}
            title="Capture Screenshot"
            disabled={isCapturing}
          >
            {isCapturing ? <Loader2 size={12} className="spin" /> : <Camera size={12} />}
            <span>{isCapturing ? 'CAPTURING...' : 'CAPTURE'}</span>
          </button>
        )}

        {/* Fullscreen Toggle Button */}
        {onToggleFullscreen && (
          <button
            onClick={onToggleFullscreen}
            className={`geo-map-action-btn geo-map-fullscreen-btn ${isFullscreen ? 'active' : ''}`}
            title={isFullscreen ? 'Exit Fullscreen' : 'Enter Fullscreen'}
          >
            {isFullscreen ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
            <span>{isFullscreen ? 'EXIT' : 'FULLSCREEN'}</span>
          </button>
        )}
      </div>

      <div className="geo-map-stats">
        <div className="geo-stat attack-counter">
          <Zap size={14} className="text-green-400" />
          <span className="counter-value">{formatAttackCount(stats.total)}</span>
          <small>Attacks</small>
        </div>
        <div className="geo-stat">
          <Globe size={14} className="text-blue-400" />
          <span>{stats.attackers}</span>
          <small>Attackers</small>
        </div>
        <div
          className={`geo-stat threat-indicator threat-${getThreatLevelLabel(threatLevel).toLowerCase()}`}
        >
          {threatLevel >= 3 ? <AlertTriangle size={14} /> : <Shield size={14} />}
          <span className="threat-text">{getThreatLevelLabel(threatLevel)}</span>
          <span className="threat-rate">{attackVelocity}/min</span>
        </div>
      </div>
    </div>
  );
};
