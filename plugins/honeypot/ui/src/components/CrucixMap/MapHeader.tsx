/**
 * MapHeader - Crucix-style stats overlay with view toggle and region selector
 */

import {
  Globe,
  Map,
  Zap,
  Activity,
  Shield,
  AlertTriangle,
  Camera,
  Loader2,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import type { MapStats } from './types';
import type { ViewMode } from './types';
import { getThreatLevel, getThreatLevelLabel, formatAttackCount } from '../geoUtils';
import { REGION_POV } from './constants';

interface MapHeaderProps {
  stats: MapStats;
  attackVelocity: number;
  viewMode: ViewMode;
  onToggleView: () => void;
  selectedRegion: string;
  onRegionChange: (region: string) => void;
  isFullscreen: boolean;
  onToggleFullscreen: () => void;
  onCapture?: () => void;
  isCapturing?: boolean;
}

export function MapHeader({
  stats,
  attackVelocity,
  viewMode,
  onToggleView,
  selectedRegion,
  onRegionChange,
  isFullscreen,
  onToggleFullscreen,
  onCapture,
  isCapturing = false,
}: MapHeaderProps) {
  const threatLevel = getThreatLevel(attackVelocity);
  const threatLabel = getThreatLevelLabel(threatLevel);

  return (
    <div className="crucix-header">
      <div className="crucix-header-left">
        <div className="crucix-title">
          <Globe size={16} />
          <span>ATTACK INTELLIGENCE MAP</span>
          <span className="crucix-status-live">
            <Zap size={10} fill="currentColor" /> LIVE
          </span>
        </div>

        {/* View toggle */}
        <button className="crucix-view-toggle" onClick={onToggleView}>
          {viewMode === 'flat' ? <Globe size={13} /> : <Map size={13} />}
          <span>{viewMode === 'flat' ? 'GLOBE MODE' : 'FLAT MODE'}</span>
        </button>

        {/* Region selector (globe only) */}
        {viewMode === 'globe' && (
          <div className="crucix-region-selector">
            {Object.keys(REGION_POV).map((region) => (
              <button
                key={region}
                className={`crucix-region-btn ${selectedRegion === region ? 'active' : ''}`}
                onClick={() => onRegionChange(region)}
              >
                {region.charAt(0).toUpperCase() + region.slice(1).replace(/([A-Z])/g, ' $1')}
              </button>
            ))}
          </div>
        )}

        {/* Capture */}
        {onCapture && (
          <button
            className={`crucix-action-btn ${isCapturing ? 'disabled' : ''}`}
            onClick={onCapture}
            disabled={isCapturing}
          >
            {isCapturing ? <Loader2 size={12} className="crucix-spin" /> : <Camera size={12} />}
          </button>
        )}

        {/* Fullscreen */}
        <button
          className={`crucix-action-btn ${isFullscreen ? 'crucix-exit-fs' : ''}`}
          onClick={onToggleFullscreen}
        >
          {isFullscreen ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
        </button>
      </div>

      <div className="crucix-header-right">
        <div className="crucix-stat">
          <Zap size={14} />
          <span className="crucix-stat-value">{formatAttackCount(stats.total)}</span>
          <small>Attacks</small>
        </div>
        <div className="crucix-stat">
          <Activity size={14} />
          <span className="crucix-stat-value">{stats.attackers}</span>
          <small>Attackers</small>
        </div>
        <div className="crucix-stat">
          <Globe size={14} />
          <span className="crucix-stat-value">{stats.countries}</span>
          <small>Countries</small>
        </div>
        <div className={`crucix-stat crucix-threat crucix-threat-${threatLevel}`}>
          {threatLevel >= 3 ? <AlertTriangle size={14} /> : <Shield size={14} />}
          <span>{threatLabel}</span>
          <small>{attackVelocity}/min</small>
        </div>
      </div>
    </div>
  );
}
