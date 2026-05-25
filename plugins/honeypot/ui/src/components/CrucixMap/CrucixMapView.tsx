/**
 * CrucixMapView - Main wrapper for Crucix-style dual-mode attack map
 *
 * Drop-in replacement for AttackGeoMap. Provides both a 2D flat map (D3 SVG)
 * and a 3D globe (Globe.gl) with a toggle between views.
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import html2canvas from 'html2canvas';
import type { CrucixMapProps, ViewMode, MapPoint, SelectedMarker, HoveredPoint } from './types';
import type { GraphNode } from '../types';
import { useMapData } from './useMapData';
import { MapHeader } from './MapHeader';
import { MapPopup } from './MapPopup';
import { GlobeView } from './GlobeView';
import { FlatMapView } from './FlatMapView';
import { SEVERITY_COLORS } from './constants';
import './CrucixMapView.css';

const CrucixMapView: React.FC<CrucixMapProps> = ({
  events = [],
  attackers = [],
  activeProtocols = [],
  honeypotContext: _honeypotContext,
  onSelectNode,
  isActive = true,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('flat');
  const [selectedRegion, setSelectedRegion] = useState('world');
  const [selectedMarker, setSelectedMarker] = useState<SelectedMarker | null>(null);
  const [hoveredPoint, setHoveredPoint] = useState<HoveredPoint | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isCapturing, setIsCapturing] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  // Track isActive in a ref for animation checks
  const isActiveRef = useRef(isActive);
  useEffect(() => {
    isActiveRef.current = isActive;
  }, [isActive]);

  // Transform data into map format
  const { points, arcs, rings, honeypot, stats, attackVelocity } = useMapData({
    events,
    attackers,
    activeProtocols,
  });

  // Track dimensions
  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  // Toggle view mode
  const handleToggleView = useCallback(() => {
    setViewMode((prev) => (prev === 'flat' ? 'globe' : 'flat'));
    setSelectedMarker(null);
  }, []);

  // Point click → show popup
  const handlePointClick = useCallback((point: MapPoint, event: MouseEvent) => {
    const container = containerRef.current;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    setSelectedMarker({
      point,
      screenX: event.clientX - rect.left,
      screenY: event.clientY - rect.top,
    });
  }, []);

  // Point hover with cursor position tracking
  const handlePointHover = useCallback((point: MapPoint | null, event?: MouseEvent) => {
    if (!point || !event || !containerRef.current) {
      setHoveredPoint(null);
      return;
    }

    const rect = containerRef.current.getBoundingClientRect();
    setHoveredPoint({
      point,
      cursorX: event.clientX - rect.left,
      cursorY: event.clientY - rect.top,
    });
  }, []);

  // Close popup
  const handleClosePopup = useCallback(() => {
    setSelectedMarker(null);
  }, []);

  // Analyze threat → create GraphNode and call onSelectNode
  const handleAnalyze = useCallback(
    (point: MapPoint) => {
      if (!onSelectNode) return;
      const graphNode: GraphNode = {
        id: `attacker-${point.ip}`,
        type: 'attacker',
        x: 0,
        y: 0,
        vx: 0,
        vy: 0,
        radius: 25,
        ip: point.ip,
        country_code: point.country_code,
        country: point.country,
        protocol: point.protocol,
        severity: point.severity,
        attackCount: point.attackCount,
        visible: true,
      };
      onSelectNode(graphNode);
      setSelectedMarker(null);
    },
    [onSelectNode]
  );

  // Fullscreen
  const handleToggleFullscreen = useCallback(() => {
    if (!containerRef.current) return;
    if (!isFullscreen) {
      containerRef.current.requestFullscreen?.().catch(console.error);
    } else {
      document.exitFullscreen?.().catch(console.error);
    }
  }, [isFullscreen]);

  useEffect(() => {
    const onChange = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', onChange);
    return () => document.removeEventListener('fullscreenchange', onChange);
  }, []);

  // Screenshot
  const handleCapture = useCallback(async () => {
    if (!containerRef.current || isCapturing) return;
    setIsCapturing(true);
    setSelectedMarker(null);

    containerRef.current.classList.add('crucix-screenshot-mode');
    await new Promise((r) => setTimeout(r, 100));

    try {
      const canvas = await html2canvas(containerRef.current, {
        backgroundColor: '#020408',
        scale: 2,
        useCORS: true,
        logging: false,
      });

      const now = new Date();
      const dateStr = now.toISOString().slice(0, 16).replace('T', '_').replace(':', '-');
      const filename = `honeypot-${viewMode}-${dateStr}.png`;

      canvas.toBlob((blob: Blob | null) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download = filename;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(url);
        }
      }, 'image/png');
    } catch (error) {
      console.error('Screenshot capture failed:', error);
    } finally {
      containerRef.current?.classList.remove('crucix-screenshot-mode');
      setIsCapturing(false);
    }
  }, [isCapturing, viewMode]);

  // Close popup on background click
  const handleContainerClick = useCallback(() => {
    if (selectedMarker) setSelectedMarker(null);
  }, [selectedMarker]);

  return (
    <div
      ref={containerRef}
      className={`crucix-container ${isFullscreen ? 'crucix-fullscreen' : ''}`}
      onClick={handleContainerClick}
    >
      <MapHeader
        stats={stats}
        attackVelocity={attackVelocity}
        viewMode={viewMode}
        onToggleView={handleToggleView}
        selectedRegion={selectedRegion}
        onRegionChange={setSelectedRegion}
        isFullscreen={isFullscreen}
        onToggleFullscreen={handleToggleFullscreen}
        onCapture={handleCapture}
        isCapturing={isCapturing}
      />

      <div className="crucix-map-area">
        {viewMode === 'flat' ? (
          <FlatMapView
            points={points}
            arcs={arcs}
            honeypot={honeypot}
            onPointClick={handlePointClick}
            onPointHover={handlePointHover}
          />
        ) : (
          <GlobeView
            points={points}
            arcs={arcs}
            rings={rings}
            honeypot={honeypot}
            isActive={isActive}
            onPointClick={handlePointClick}
            onPointHover={handlePointHover}
            selectedRegion={selectedRegion}
          />
        )}
      </div>

      {/* Popup */}
      {selectedMarker && (
        <MapPopup
          point={selectedMarker.point}
          screenX={selectedMarker.screenX}
          screenY={selectedMarker.screenY}
          containerWidth={dimensions.width}
          containerHeight={dimensions.height}
          onClose={handleClosePopup}
          onAnalyze={handleAnalyze}
        />
      )}

      {/* Hover tooltip with dynamic positioning */}
      {hoveredPoint &&
        !selectedMarker &&
        (() => {
          const tooltipWidth = 200; // Approximate width
          const tooltipHeight = 40; // Approximate height
          const offset = 15; // Offset from cursor
          const padding = 10; // Padding from edges

          // Calculate position with smart edge detection
          let left = hoveredPoint.cursorX + offset;
          let top = hoveredPoint.cursorY - tooltipHeight / 2;

          // Adjust horizontal position if too close to right edge
          if (left + tooltipWidth + padding > dimensions.width) {
            left = hoveredPoint.cursorX - tooltipWidth - offset;
          }

          // Adjust horizontal position if too close to left edge
          if (left < padding) {
            left = padding;
          }

          // Adjust vertical position if too close to top edge
          if (top < padding) {
            top = hoveredPoint.cursorY + offset;
          }

          // Adjust vertical position if too close to bottom edge
          if (top + tooltipHeight + padding > dimensions.height) {
            top = hoveredPoint.cursorY - tooltipHeight - offset;
          }

          return (
            <div
              className="crucix-hover-tooltip"
              style={{
                left: `${left}px`,
                top: `${top}px`,
              }}
            >
              <span className="crucix-hover-flag">
                {String.fromCodePoint(
                  ...(hoveredPoint.point.country_code || 'UN')
                    .toUpperCase()
                    .split('')
                    .map((c) => 0x1f1e6 + c.charCodeAt(0) - 65)
                )}
              </span>
              <span className="crucix-hover-ip">{hoveredPoint.point.ip}</span>
              <span
                className="crucix-hover-protocol"
                style={{
                  background: (SEVERITY_COLORS[hoveredPoint.point.severity] || '#44ccff') + '30',
                  color: SEVERITY_COLORS[hoveredPoint.point.severity] || '#44ccff',
                }}
              >
                {hoveredPoint.point.protocol.toUpperCase()}
              </span>
            </div>
          );
        })()}

      {/* Legend */}
      <div className="crucix-legend">
        <div className="crucix-legend-title">SEVERITY</div>
        {Object.entries(SEVERITY_COLORS).map(([level, color]) => (
          <div key={level} className="crucix-legend-item">
            <span
              className="crucix-legend-dot"
              style={{ background: color, boxShadow: `0 0 6px ${color}` }}
            />
            <span className="crucix-legend-label">{level}</span>
          </div>
        ))}
      </div>

      {/* Hint */}
      <div className="crucix-hint">
        {viewMode === 'flat'
          ? 'Scroll to zoom \u2022 Drag to pan \u2022 Click marker for details'
          : 'Drag to rotate \u2022 Scroll to zoom \u2022 Click marker for details'}
      </div>

      {/* CRT scanlines */}
      <div className="crucix-scanlines" />
      {/* Vignette */}
      <div className="crucix-vignette" />
    </div>
  );
};

export default React.memo(CrucixMapView);
