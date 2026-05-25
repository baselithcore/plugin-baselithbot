/**
 * GlobeView - Crucix-style 3D Globe using Globe.gl
 *
 * WebGL globe with attacker points, attack arcs, and pulsing conflict rings.
 * Implements starfield background, auto-rotation, and zoom-aware rendering.
 * Optimized for high point counts with priority-based filtering.
 */

import { useEffect, useRef, useMemo, useCallback } from 'react';
import Globe from 'globe.gl';
import * as THREE from 'three';
import type { MapPoint, MapArc, MapRing } from './types';
import { GLOBE_CONFIG, REGION_POV } from './constants';

interface GlobeViewProps {
  points: MapPoint[];
  arcs: MapArc[];
  rings: MapRing[];
  honeypot: { lat: number; lng: number };
  isActive: boolean;
  onPointClick?: (point: MapPoint, event: MouseEvent) => void;
  onPointHover?: (point: MapPoint | null, event?: MouseEvent) => void;
  selectedRegion?: string;
}

// Max points to render based on camera altitude
const MAX_POINTS_FAR = 500;
const MAX_POINTS_CLOSE = 2000;

export function GlobeView({
  points,
  arcs,
  rings,
  honeypot,
  isActive,
  onPointClick,
  onPointHover,
  selectedRegion = 'world',
}: GlobeViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<any>(null);
  const autoRotateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const currentAltitudeRef = useRef(1.8);
  const tooltipDelayRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hoveredPointRef = useRef<MapPoint | null>(null);
  const lastMouseEventRef = useRef<MouseEvent | null>(null);

  // Filter points based on camera altitude and priority
  const visiblePoints = useMemo(() => {
    const altitude = currentAltitudeRef.current;
    const maxPoints = altitude < 1.5 ? MAX_POINTS_CLOSE : MAX_POINTS_FAR;

    // Sort by priority (1 = highest) and recency
    const sorted = [...points].sort((a, b) => {
      if (a.priority !== b.priority) return a.priority - b.priority;
      if (a.isRecent !== b.isRecent) return a.isRecent ? -1 : 1;
      return b.attackCount - a.attackCount;
    });

    // At high altitude (far away), show only high-priority points
    if (altitude > 2.5) {
      return sorted.filter((p) => p.priority <= 2).slice(0, maxPoints);
    } else if (altitude > 1.5) {
      return sorted.slice(0, maxPoints);
    }

    return sorted.slice(0, maxPoints);
  }, [points]);

  // Two-level hover system (same as FlatMapView):
  // 1. Immediate visual feedback (handled by Globe.gl pointColor/pointRadius change)
  // 2. Delayed tooltip (300ms) to prevent spam during rotation/zoom
  const showTooltipDelayed = useCallback(
    (point: MapPoint) => {
      // Clear any existing timeout
      if (tooltipDelayRef.current) {
        clearTimeout(tooltipDelayRef.current);
      }
      // Set new timeout for tooltip display
      tooltipDelayRef.current = setTimeout(() => {
        onPointHover?.(point, lastMouseEventRef.current || undefined);
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
    hoveredPointRef.current = null;
  }, [onPointHover]);

  // Cleanup tooltip timeout on unmount
  useEffect(() => {
    return () => {
      if (tooltipDelayRef.current) {
        clearTimeout(tooltipDelayRef.current);
      }
    };
  }, []);

  // Initialize globe
  useEffect(() => {
    if (!containerRef.current) return;

    const el = containerRef.current;
    const globeInstance = Globe()(el);

    // Configure globe appearance
    globeInstance
      .globeImageUrl(GLOBE_CONFIG.EARTH_IMG)
      .bumpImageUrl(GLOBE_CONFIG.BUMP_IMG)
      .backgroundColor('rgba(0,0,0,0)')
      .atmosphereColor(GLOBE_CONFIG.ATMOSPHERE_COLOR)
      .atmosphereAltitude(GLOBE_CONFIG.ATMOSPHERE_ALTITUDE)
      .showGraticules(true);

    // Points layer — refined marker sizing with severity-based visual hierarchy
    globeInstance
      .pointsData([])
      .pointLat('lat')
      .pointLng('lng')
      .pointAltitude('altitude')
      .pointRadius((d: any) => {
        const camLen = globeInstance.camera().position.length();
        const globeR = globeInstance.getGlobeRadius();
        const altitude = camLen / globeR;
        currentAltitudeRef.current = altitude;

        const isHovered = hoveredPointRef.current?.id === d.id;
        const hoverScale = isHovered ? 1.5 : 1;

        // Severity-based size hierarchy — critical threats are clearly larger
        const severityScale =
          d.severity === 'critical'
            ? 1.6
            : d.severity === 'high'
              ? 1.3
              : d.severity === 'medium'
                ? 1.05
                : 0.85;

        // Attack count adds subtle weight
        const countScale = 1 + Math.log10(d.attackCount + 1) * 0.1;

        // Camera-aware scaling — grow slightly when zoomed in, cap when far
        const altScale = Math.min(1.6, 1.0 / Math.max(altitude, 0.5));

        // Base size is larger for better visibility
        const baseSize = Math.max(d.size, 0.18);

        return Math.min(1.4, baseSize * severityScale * countScale * altScale * hoverScale);
      })
      .pointColor((d: any) => {
        // Immediate visual feedback: brighten color on hover
        const isHovered = hoveredPointRef.current?.id === d.id;
        const baseColor = d.color || 'rgba(100,240,200,0.9)';

        // Professional, balanced opacity to ensure a sleek look without bloating
        const opacity = d.priority === 1 ? 0.95 : d.priority === 2 ? 0.8 : 0.6;

        // If hovered, increase brightness and opacity
        if (isHovered) {
          // Parse RGBA and increase RGB values
          const match = baseColor.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
          if (match) {
            const r = Math.min(255, Math.floor(parseInt(match[1]) * 1.4));
            const g = Math.min(255, Math.floor(parseInt(match[2]) * 1.4));
            const b = Math.min(255, Math.floor(parseInt(match[3]) * 1.4));
            return `rgba(${r},${g},${b},1)`;
          }
        }

        return baseColor.replace(/[\d.]+\)$/, `${opacity})`);
      })
      .pointLabel('')
      .onPointClick((point: any, event: MouseEvent) => {
        onPointClick?.(point as MapPoint, event);
      })
      .onPointHover((point: any) => {
        const mapPoint = point as MapPoint | null;

        if (mapPoint) {
          // Store hovered point for immediate visual feedback
          hoveredPointRef.current = mapPoint;

          // Stop auto-rotation
          const ctrl = globeInstance.controls() as any;
          ctrl.autoRotate = false;

          // Delayed tooltip display
          showTooltipDelayed(mapPoint);
        } else {
          // Clear hover state
          hoveredPointRef.current = null;

          // Hide tooltip immediately
          hideTooltip();
        }
      });

    // Arcs layer — subtle flowing animation from attacker → honeypot
    // Very long dash + micro gap = arc is ~99% visible, with a luminous
    // seam that slowly glides along it to convey "data in transit"
    globeInstance
      .arcsData([])
      .arcStartLat('startLat')
      .arcStartLng('startLng')
      .arcEndLat('endLat')
      .arcEndLng('endLng')
      .arcColor('color')
      .arcStroke((d: any) => {
        // Severity-based stroke: critical connections are bolder
        const severityStroke =
          d.severity === 'critical'
            ? 0.7
            : d.severity === 'high'
              ? 0.55
              : d.severity === 'medium'
                ? 0.4
                : 0.3;
        // Blend with attack-count-based stroke, keeping it refined
        const countStroke = Math.min(0.8, 0.2 + Math.log10((d.attackCount || 1) + 1) * 0.15);
        return Math.min(0.9, Math.max(severityStroke, countStroke));
      })
      .arcDashLength(0.8)
      .arcDashGap(0.01)
      .arcDashAnimateTime(5000)
      .arcAltitudeAutoScale(0.3)
      .arcLabel('');

    // Rings layer
    globeInstance
      .ringsData([])
      .ringLat('lat')
      .ringLng('lng')
      .ringMaxRadius('maxR')
      .ringPropagationSpeed('propagationSpeed')
      .ringRepeatPeriod('repeatPeriod')
      .ringColor(() => (t: number) => `rgba(255, 71, 87, ${Math.max(0, (1 - t) * 0.4)})`);

    globeRef.current = globeInstance;

    // Configure controls
    const controls = globeInstance.controls() as any;
    controls.autoRotate = true;
    controls.autoRotateSpeed = GLOBE_CONFIG.AUTO_ROTATE_SPEED;
    controls.enableDamping = true;
    controls.dampingFactor = GLOBE_CONFIG.DAMPING_FACTOR;
    controls.minDistance = 150;
    controls.maxDistance = 650;

    // Resume auto-rotate after inactivity
    const onInteraction = () => {
      controls.autoRotate = false;
      if (autoRotateTimerRef.current) clearTimeout(autoRotateTimerRef.current);
      autoRotateTimerRef.current = setTimeout(() => {
        controls.autoRotate = true;
      }, 10000);
    };

    // Track mouse movement for tooltip positioning
    const onMouseMove = (e: Event) => {
      lastMouseEventRef.current = e as MouseEvent;
    };

    el.addEventListener('mousedown', onInteraction);
    el.addEventListener('wheel', onInteraction);
    el.addEventListener('touchstart', onInteraction);
    el.addEventListener('mousemove', onMouseMove);

    // Override graticule colors
    const scene = globeInstance.scene();
    scene.traverse((obj: THREE.Object3D) => {
      if ((obj as THREE.Line).isLine) {
        const mat = (obj as THREE.Line).material as THREE.LineBasicMaterial;
        if (mat && mat.color) {
          mat.color.setHex(GLOBE_CONFIG.GRATICULE_COLOR);
          mat.opacity = GLOBE_CONFIG.GRATICULE_OPACITY;
          mat.transparent = true;
        }
      }
    });

    // Add ambient lighting to brighten the globe
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(ambientLight);

    // Add directional light for better depth perception
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.6);
    directionalLight.position.set(-1, 1, 1);
    scene.add(directionalLight);

    // Add starfield
    const starGeometry = new THREE.BufferGeometry();
    const starPositions = new Float32Array(GLOBE_CONFIG.STARFIELD_COUNT * 3);
    for (let i = 0; i < GLOBE_CONFIG.STARFIELD_COUNT; i++) {
      const r = 800 + Math.random() * 400;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      starPositions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      starPositions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      starPositions[i * 3 + 2] = r * Math.cos(phi);
    }
    starGeometry.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
    const starMaterial = new THREE.PointsMaterial({
      color: 0xffffff,
      size: 0.7,
      transparent: true,
      opacity: 0.8,
      sizeAttenuation: true,
    });
    const stars = new THREE.Points(starGeometry, starMaterial);
    scene.add(stars);

    // Honeypot marker — core sphere + translucent glow ring
    const latRad = (honeypot.lat * Math.PI) / 180;
    const lngRad = (honeypot.lng * Math.PI) / 180;
    const hpR = globeInstance.getGlobeRadius() + 1.5;

    const hpPos = new THREE.Vector3(
      hpR * Math.cos(latRad) * Math.sin(lngRad),
      hpR * Math.sin(latRad),
      hpR * Math.cos(latRad) * Math.cos(lngRad)
    );

    // Core dot
    const hpGeo = new THREE.SphereGeometry(1.8, 24, 24);
    const hpMat = new THREE.MeshBasicMaterial({ color: 0x64f0c8 });
    const hpMesh = new THREE.Mesh(hpGeo, hpMat);
    hpMesh.position.copy(hpPos);
    scene.add(hpMesh);

    // Glow ring around honeypot
    const ringGeo = new THREE.RingGeometry(3.2, 4.0, 48);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0x64f0c8,
      transparent: true,
      opacity: 0.35,
      side: THREE.DoubleSide,
    });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.position.copy(hpPos);
    // Orient ring to face outward from globe surface
    ringMesh.lookAt(new THREE.Vector3(0, 0, 0));
    scene.add(ringMesh);

    // Set initial POV
    const initialPov = REGION_POV[selectedRegion] || REGION_POV.world;
    globeInstance.pointOfView(initialPov, 0);

    // Handle resize
    const onResize = () => {
      if (el) {
        globeInstance.width(el.clientWidth);
        globeInstance.height(el.clientHeight);
      }
    };

    const ro = new ResizeObserver(onResize);
    ro.observe(el);
    onResize();

    return () => {
      ro.disconnect();
      el.removeEventListener('mousedown', onInteraction);
      el.removeEventListener('wheel', onInteraction);
      el.removeEventListener('touchstart', onInteraction);
      el.removeEventListener('mousemove', onMouseMove);
      if (autoRotateTimerRef.current) clearTimeout(autoRotateTimerRef.current);
      // Clean up globe
      globeInstance._destructor?.();
    };
  }, []); // Only init once

  // Update data when props change
  useEffect(() => {
    const globe = globeRef.current;
    if (!globe) return;
    console.log(
      '[GlobeView] Updating points, total:',
      points.length,
      'visible:',
      visiblePoints.length
    );
    if (visiblePoints.length > 0) {
      console.log('[GlobeView] First visible point:', visiblePoints[0]);
    }
    // Clear hover state when points change
    hoveredPointRef.current = null;
    globe.pointsData(visiblePoints);
  }, [points, visiblePoints]);

  // Filter arcs to only show for visible points (performance optimization)
  const visibleArcs = useMemo(() => {
    const visibleIpSet = new Set(visiblePoints.map((p) => p.ip));
    return arcs.filter((arc) => {
      // Extract IP from arc id (format: "arc-{ip}")
      const arcIp = arc.id.replace('arc-', '');
      return visibleIpSet.has(arcIp);
    });
  }, [arcs, visiblePoints]);

  useEffect(() => {
    const globe = globeRef.current;
    if (!globe) return;
    globe.arcsData(visibleArcs);
  }, [visibleArcs]);

  useEffect(() => {
    const globe = globeRef.current;
    if (!globe) return;
    globe.ringsData(rings);
  }, [rings]);

  // Navigate to region
  useEffect(() => {
    const globe = globeRef.current;
    if (!globe) return;
    const pov = REGION_POV[selectedRegion] || REGION_POV.world;
    globe.pointOfView(pov, 1000);
  }, [selectedRegion]);

  // Pause/resume animation
  useEffect(() => {
    const globe = globeRef.current;
    if (!globe) return;

    if (!isActive) {
      globe.pauseAnimation?.();
    } else {
      globe.resumeAnimation?.();
    }
  }, [isActive]);

  return (
    <div
      ref={containerRef}
      className="crucix-globe-container"
      style={{ width: '100%', height: '100%', cursor: 'grab' }}
    />
  );
}
