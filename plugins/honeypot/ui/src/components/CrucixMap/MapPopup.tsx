/**
 * MapPopup - Crucix-style glass-morphism popup for marker details
 */

import { useEffect, useRef } from 'react';
import { X, ExternalLink } from 'lucide-react';
import type { MapPoint } from './types';
import { SEVERITY_COLORS } from './constants';
import { getCountryFlag, getCountryName } from '../geoUtils';
import { normalizeIpDisplay } from '../api';

interface MapPopupProps {
  point: MapPoint;
  screenX: number;
  screenY: number;
  containerWidth: number;
  containerHeight: number;
  onClose: () => void;
  onAnalyze?: (point: MapPoint) => void;
}

export function MapPopup({
  point,
  screenX,
  screenY,
  containerWidth,
  containerHeight,
  onClose,
  onAnalyze,
}: MapPopupProps) {
  const ref = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  // Smart positioning
  const popWidth = 240;
  const popHeight = 200;
  const pad = 16;
  let left = screenX + 20;
  let top = screenY - popHeight / 2;

  if (left + popWidth + pad > containerWidth) left = screenX - popWidth - 20;
  if (left < pad) left = pad;
  if (top < pad) top = pad;
  if (top + popHeight + pad > containerHeight) top = containerHeight - popHeight - pad;

  const sevColor = SEVERITY_COLORS[point.severity] || SEVERITY_COLORS.info;
  const flag = getCountryFlag(point.country_code);
  const countryName = getCountryName(point.country_code);

  return (
    <div
      ref={ref}
      className="crucix-popup"
      style={{ left: `${left}px`, top: `${top}px` }}
      onClick={(e) => e.stopPropagation()}
    >
      {/* Header */}
      <div className="crucix-popup-header">
        <span className="crucix-popup-flag">{flag}</span>
        <div className="crucix-popup-title">
          <span className="crucix-popup-ip">{normalizeIpDisplay(point.ip)}</span>
          <span className="crucix-popup-location">{countryName || point.country}</span>
        </div>
        <button className="crucix-popup-close" onClick={onClose} aria-label="Close">
          <X size={14} />
        </button>
      </div>

      {/* Stats */}
      <div className="crucix-popup-stats">
        <div className="crucix-popup-row">
          <span className="crucix-popup-label">PROTOCOL</span>
          <span className="crucix-popup-badge" data-type={point.protocol}>
            {point.protocol.toUpperCase()}
          </span>
        </div>
        <div className="crucix-popup-row">
          <span className="crucix-popup-label">SEVERITY</span>
          <span
            className="crucix-popup-badge"
            style={{ background: sevColor + '25', color: sevColor }}
          >
            {point.severity.toUpperCase()}
          </span>
        </div>
        <div className="crucix-popup-row">
          <span className="crucix-popup-label">ATTACKS</span>
          <span className="crucix-popup-value">{point.attackCount.toLocaleString()}</span>
        </div>
      </div>

      {/* Action */}
      {onAnalyze && (
        <div className="crucix-popup-actions">
          <button className="crucix-popup-btn" onClick={() => onAnalyze(point)}>
            <ExternalLink size={12} strokeWidth={2.5} />
            <span>Analyze Threat</span>
          </button>
        </div>
      )}
    </div>
  );
}
