/**
 * FlatMapView - Crucix-style 2D SVG flat map using D3.js
 *
 * Natural Earth projection with country borders, attacker markers,
 * great-circle arcs, zoom/pan, and zoom-aware marker sizing.
 */

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import * as d3 from 'd3';
import * as topojson from 'topojson-client';
import type { MapPoint, MapArc } from './types';
import { FLAT_MAP_CONFIG } from './constants';

interface FlatMapViewProps {
  points: MapPoint[];
  arcs: MapArc[];
  honeypot: { lat: number; lng: number };
  onPointClick?: (point: MapPoint, event: MouseEvent) => void;
  onPointHover?: (point: MapPoint | null, event?: MouseEvent) => void;
}

// Max points to render based on zoom level
const MAX_POINTS_BASE = 500;
const MAX_POINTS_ZOOMED = 2000;

export function FlatMapView({
  points,
  arcs,
  honeypot,
  onPointClick,
  onPointHover,
}: FlatMapViewProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const projectionRef = useRef<d3.GeoProjection | null>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const countriesDataRef = useRef<any>(null);
  const [dataLoaded, setDataLoaded] = useState(false);
  const currentZoomRef = useRef(1);
  const hoveredMarkerRef = useRef<any>(null);
  const tooltipDelayRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Filter points based on zoom level and priority
  const visiblePoints = useMemo(() => {
    const zoom = currentZoomRef.current;
    const maxPoints = zoom >= 2 ? MAX_POINTS_ZOOMED : MAX_POINTS_BASE;

    // Sort by priority (1 = highest) and recency
    const sorted = [...points].sort((a, b) => {
      if (a.priority !== b.priority) return a.priority - b.priority;
      if (a.isRecent !== b.isRecent) return a.isRecent ? -1 : 1;
      return b.attackCount - a.attackCount;
    });

    // At low zoom, show only high-priority points
    if (zoom < 1.5) {
      return sorted.filter((p) => p.priority <= 2).slice(0, maxPoints);
    } else if (zoom < 3) {
      return sorted.slice(0, maxPoints);
    }

    return sorted.slice(0, maxPoints);
  }, [points]);

  // Two-level hover system:
  // 1. Immediate visual feedback (handled in event handlers)
  // 2. Delayed tooltip (300ms) to prevent spam during pan/zoom
  const showTooltipDelayed = useCallback(
    (point: MapPoint, event: MouseEvent) => {
      // Clear any existing timeout
      if (tooltipDelayRef.current) {
        clearTimeout(tooltipDelayRef.current);
      }
      // Set new timeout for tooltip display
      tooltipDelayRef.current = setTimeout(() => {
        onPointHover?.(point, event);
      }, 300); // 300ms delay for tooltip
    },
    [onPointHover]
  );

  const hideTooltip = useCallback(() => {
    // Clear timeout and hide immediately
    if (tooltipDelayRef.current) {
      clearTimeout(tooltipDelayRef.current);
      tooltipDelayRef.current = null;
    }
    onPointHover?.(null);
  }, [onPointHover]);

  // Cleanup tooltip timeout on unmount
  useEffect(() => {
    return () => {
      if (tooltipDelayRef.current) {
        clearTimeout(tooltipDelayRef.current);
      }
    };
  }, []);

  // Fetch country geometry
  useEffect(() => {
    fetch(FLAT_MAP_CONFIG.COUNTRIES_URL)
      .then((r) => r.json())
      .then((data) => {
        countriesDataRef.current = data;
        setDataLoaded(true);
      })
      .catch(console.error);
  }, []);

  // Handle resize
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    const onResize = () => {
      const parent = svg.parentElement;
      if (parent) {
        setDimensions({ width: parent.clientWidth, height: parent.clientHeight });
      }
    };

    const ro = new ResizeObserver(onResize);
    ro.observe(svg.parentElement!);
    onResize();
    return () => ro.disconnect();
  }, []);

  // Initialize and render the map
  useEffect(() => {
    if (!svgRef.current || !dataLoaded || !countriesDataRef.current) return;
    if (dimensions.width === 0 || dimensions.height === 0) return;

    const svg = d3.select(svgRef.current);
    const { width, height } = dimensions;

    // Clear previous render
    svg.selectAll('*').remove();

    // Projection
    const projection = d3
      .geoNaturalEarth1()
      .fitSize([width, height], { type: 'Sphere' } as any)
      .translate([width / 2, height / 2]);
    projectionRef.current = projection;

    const path = d3.geoPath(projection);

    // Main group (transformed by zoom)
    const g = svg.append('g').attr('class', 'map-group');

    // Background ocean
    g.append('path')
      .datum({ type: 'Sphere' } as any)
      .attr('d', path as any)
      .attr('fill', FLAT_MAP_CONFIG.BG_COLOR)
      .attr('stroke', 'none');

    // Graticule
    const graticule = d3.geoGraticule();
    g.append('path')
      .datum(graticule())
      .attr('class', 'crucix-graticule')
      .attr('d', path as any)
      .attr('fill', 'none')
      .attr('stroke', FLAT_MAP_CONFIG.GRATICULE_STROKE)
      .attr('stroke-width', 0.5);

    // Countries
    const countries = topojson.feature(
      countriesDataRef.current,
      countriesDataRef.current.objects.countries
    ) as any;

    g.selectAll('.crucix-country')
      .data(countries.features)
      .enter()
      .append('path')
      .attr('class', 'crucix-country')
      .attr('d', path as any)
      .attr('fill', FLAT_MAP_CONFIG.LAND_FILL)
      .attr('stroke', FLAT_MAP_CONFIG.LAND_STROKE)
      .attr('stroke-width', 0.5)
      .on('mouseenter', function () {
        d3.select(this).attr('fill', FLAT_MAP_CONFIG.LAND_HOVER_FILL);
      })
      .on('mouseleave', function () {
        d3.select(this).attr('fill', FLAT_MAP_CONFIG.LAND_FILL);
      });

    // Country borders
    const borders = topojson.mesh(
      countriesDataRef.current,
      countriesDataRef.current.objects.countries,
      (a: any, b: any) => a !== b
    );
    g.append('path')
      .datum(borders)
      .attr('class', 'crucix-borders')
      .attr('d', path as any)
      .attr('fill', 'none')
      .attr('stroke', FLAT_MAP_CONFIG.BORDER_STROKE)
      .attr('stroke-width', 0.3);

    // Arc layer
    const arcLayer = g.append('g').attr('class', 'crucix-arcs-layer');

    // Marker layer
    const markerLayer = g.append('g').attr('class', 'crucix-markers-layer');

    // Honeypot marker
    const hpPos = projection([honeypot.lng, honeypot.lat]);
    if (hpPos) {
      const hpGroup = markerLayer
        .append('g')
        .attr('transform', `translate(${hpPos[0]},${hpPos[1]})`);

      // Pulsing ring
      hpGroup
        .append('circle')
        .attr('r', 8)
        .attr('fill', 'none')
        .attr('stroke', '#64f0c8')
        .attr('stroke-width', 1.5)
        .attr('opacity', 0.6)
        .attr('class', 'crucix-hp-pulse');

      // Core dot
      hpGroup
        .append('circle')
        .attr('r', 4)
        .attr('fill', '#64f0c8')
        .attr('stroke', '#020408')
        .attr('stroke-width', 1);

      // Label
      hpGroup
        .append('text')
        .attr('y', -14)
        .attr('text-anchor', 'middle')
        .attr('fill', '#64f0c8')
        .attr('font-size', '9px')
        .attr('font-weight', '700')
        .attr('letter-spacing', '1px')
        .attr('font-family', "'IBM Plex Mono', monospace")
        .text('HONEYPOT');
    }

    // Zoom behavior
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent(FLAT_MAP_CONFIG.ZOOM_EXTENT)
      .on('zoom', (event) => {
        const { transform } = event;

        // Apply transform to main group - this moves and scales everything
        g.attr('transform', transform.toString());
        currentZoomRef.current = transform.k;

        // Inverse scale to keep visual elements at consistent screen size
        const invScale = 1 / transform.k;

        // Scale the marker CHILDREN (circles, text) inversely, not the marker group itself
        // This way the position stays fixed by parent transform, but visual size is consistent
        markerLayer.selectAll('.crucix-marker-glow').attr('transform', `scale(${invScale})`);
        markerLayer.selectAll('.crucix-marker-core').attr('transform', `scale(${invScale})`);

        // Scale honeypot marker pulse ring
        if (hpPos) {
          markerLayer.select('.crucix-hp-pulse').attr('r', 8 * invScale);
        }

        // Scale arc strokes
        arcLayer
          .selectAll<SVGGElement, MapArc>('.crucix-arc')
          .attr('stroke-width', (d) => d.stroke * invScale);
      });

    zoomRef.current = zoom;
    svg.call(zoom);

    // Store references for data updates
    (svg.node() as any).__arcLayer = arcLayer;
    (svg.node() as any).__markerLayer = markerLayer;
    (svg.node() as any).__projection = projection;
  }, [dataLoaded, dimensions, honeypot]);

  // Update arcs when data changes
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const arcLayer = (svg.node() as any)?.__arcLayer;
    const projection = (svg.node() as any)?.__projection;
    if (!arcLayer || !projection) return;

    // Draw great-circle arcs
    const arcSel = arcLayer.selectAll('.crucix-arc').data(arcs, (d: any) => d.id);

    arcSel.exit().transition().duration(300).attr('opacity', 0).remove();

    const arcEnter = arcSel
      .enter()
      .append('path')
      .attr('class', 'crucix-arc')
      .attr('fill', 'none')
      .attr('opacity', 0);

    arcEnter
      .merge(arcSel as any)
      .attr('d', (d: MapArc) => {
        // Great-circle arc using d3.geoInterpolate
        const start: [number, number] = [d.startLng, d.startLat];
        const end: [number, number] = [d.endLng, d.endLat];
        const interpolate = d3.geoInterpolate(start, end);

        const numSegments = 40;
        const lineCoords: [number, number][] = [];
        for (let i = 0; i <= numSegments; i++) {
          lineCoords.push(interpolate(i / numSegments) as [number, number]);
        }

        const lineFeature = {
          type: 'Feature' as const,
          geometry: { type: 'LineString' as const, coordinates: lineCoords },
          properties: {},
        };

        return d3.geoPath(projection)(lineFeature as any);
      })
      .attr('stroke', (d: MapArc) => d.color[0])
      .attr('stroke-width', (d: MapArc) => d.stroke / currentZoomRef.current)
      .attr('stroke-dasharray', '6 3')
      .attr('class', 'crucix-arc crucix-arc-animated')
      .transition()
      .duration(500)
      .attr('opacity', 0.7);
  }, [arcs]);

  // Update markers when data changes
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const markerLayer = (svg.node() as any)?.__markerLayer;
    const projection = (svg.node() as any)?.__projection;
    if (!markerLayer || !projection) return;

    console.log(
      '[FlatMapView] Updating markers, total:',
      points.length,
      'visible:',
      visiblePoints.length,
      'zoom:',
      currentZoomRef.current
    );
    if (visiblePoints.length > 0) {
      console.log('[FlatMapView] First visible point:', visiblePoints[0]);
    }

    // Inverse scale for consistent visual size at any zoom level
    const currentZoom = currentZoomRef.current;
    const invScale = 1 / currentZoom;

    const markerSel = markerLayer.selectAll('.crucix-marker').data(visiblePoints, (d: any) => d.id);

    markerSel.exit().transition().duration(300).attr('opacity', 0).remove();

    const markerEnter = markerSel
      .enter()
      .append('g')
      .attr('class', 'crucix-marker')
      .attr('cursor', 'pointer')
      .attr('opacity', 0)
      .on('click', (event: MouseEvent, d: MapPoint) => {
        event.stopPropagation();
        onPointClick?.(d, event);
      })
      .on('mouseenter', function (this: SVGGElement, event: MouseEvent, d: MapPoint) {
        // Immediate visual feedback: add hover class
        d3.select(this).classed('hovered', true);

        // Store reference to hovered marker
        hoveredMarkerRef.current = this;

        // Delayed tooltip display (300ms) with cursor position
        showTooltipDelayed(d, event);
      })
      .on('mouseleave', function (this: SVGGElement) {
        // Immediate visual feedback: remove hover class
        d3.select(this).classed('hovered', false);

        // Clear reference
        if (hoveredMarkerRef.current === this) {
          hoveredMarkerRef.current = null;
        }

        // Hide tooltip immediately
        hideTooltip();
      });

    // Outer glow ring - size based on severity
    markerEnter
      .append('circle')
      .attr('class', 'crucix-marker-glow')
      .attr('r', (d: MapPoint) => {
        const baseSize = 6;
        const severityMultiplier =
          d.severity === 'critical' ? 1.3 : d.severity === 'high' ? 1.15 : 1;
        return baseSize * severityMultiplier;
      })
      .attr('fill', 'none')
      .attr('stroke-width', (d: MapPoint) => (d.severity === 'critical' ? 1.2 : 0.8))
      .attr('transform', `scale(${invScale})`); // Scale children, not parent

    // Core circle - size based on attack count and severity
    markerEnter
      .append('circle')
      .attr('class', 'crucix-marker-core')
      .attr('r', (d: MapPoint) => {
        const baseSize = 3;
        const countMultiplier = 1 + Math.log10(d.attackCount + 1) * 0.2;
        const severityMultiplier =
          d.severity === 'critical' ? 1.3 : d.severity === 'high' ? 1.15 : 1;
        return baseSize * countMultiplier * severityMultiplier;
      })
      .attr('transform', `scale(${invScale})`); // Scale children, not parent

    // Note: Static label text has been removed to reduce visual clutter.
    // Full IP details are now exclusively displayed on hover via the dynamic HTML tooltip.

    // Merge
    const merged = markerEnter.merge(markerSel as any);

    // Set marker position using ONLY translate - NO scale on the group
    // The children are scaled individually to maintain constant visual size
    merged.each(function (this: SVGGElement, d: MapPoint) {
      const pos = projection([d.lng, d.lat]);
      if (pos) {
        const elem = d3.select(this);
        // Set position - this will NEVER change during zoom
        elem.attr('transform', `translate(${pos[0]},${pos[1]})`);
      }
    });

    merged.attr('data-priority', (d: MapPoint) => d.priority);

    merged
      .select('.crucix-marker-glow')
      .attr('stroke', (d: MapPoint) => d.color)
      .attr('r', (d: MapPoint) => {
        const baseSize = 6;
        const severityMultiplier =
          d.severity === 'critical' ? 1.3 : d.severity === 'high' ? 1.15 : 1;
        return baseSize * severityMultiplier;
      })
      .attr('stroke-width', (d: MapPoint) => (d.severity === 'critical' ? 1.2 : 0.8))
      .attr('opacity', (d: MapPoint) => {
        if (d.priority === 1) return 0.9;
        if (d.priority === 2) return 0.7;
        return 0.45;
      })
      .attr('class', (d: MapPoint) =>
        d.isRecent || d.severity === 'critical'
          ? 'crucix-marker-glow crucix-marker-pulse'
          : 'crucix-marker-glow'
      );

    merged
      .select('.crucix-marker-core')
      .attr('fill', (d: MapPoint) => d.color)
      .attr('r', (d: MapPoint) => {
        const baseSize = 3;
        const countMultiplier = 1 + Math.log10(d.attackCount + 1) * 0.2;
        const severityMultiplier =
          d.severity === 'critical' ? 1.3 : d.severity === 'high' ? 1.15 : 1;
        return baseSize * countMultiplier * severityMultiplier;
      })
      .attr('stroke', '#020408')
      .attr('stroke-width', 0.4)
      .attr('opacity', (d: MapPoint) => {
        if (d.priority === 1) return 1;
        if (d.priority === 2) return 0.85;
        return 0.6;
      });

    merged.transition().duration(400).attr('opacity', 1);
  }, [points, onPointClick, onPointHover]);

  return (
    <div className="crucix-flat-container" style={{ width: '100%', height: '100%' }}>
      <svg
        ref={svgRef}
        className="crucix-flat-svg"
        width={dimensions.width}
        height={dimensions.height}
        style={{ width: '100%', height: '100%' }}
      />
    </div>
  );
}
