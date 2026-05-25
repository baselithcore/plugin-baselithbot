import { useCallback, useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { GraphNode } from '../types';

interface UseForceSimulationProps {
  nodesRef: React.MutableRefObject<Map<string, GraphNode>>;
  width: number;
  height: number;
  projection?: d3.GeoProjection;
}

import { getCountryCoordinates } from '../geoUtils/countryCoordinates';

// Boundary padding to ensure nodes (including labels) stay visible
// Node base radius is 28px + labels can extend ~50px, so 80px gives safe margin
const BOUNDARY_PADDING = 80;

// Helper to clamp a value to safe bounds relative to canvas center
const clampToBounds = (value: number, halfDimension: number): number => {
  const safeHalf = halfDimension - BOUNDARY_PADDING;
  return Math.max(-safeHalf, Math.min(safeHalf, value));
};

/**
 * Custom force that actively pushes nodes away from boundaries
 * This is stronger than just clamping post-tick because it integrates with
 * the simulation and creates a "soft boundary" effect
 */
const forceBoundingBox = (
  width: number,
  height: number,
  padding: number = BOUNDARY_PADDING,
  strength: number = 0.5
) => {
  let nodes: GraphNode[] = [];

  const force = (alpha: number) => {
    const halfWidth = width / 2 - padding;
    const halfHeight = height / 2 - padding;
    const effectiveStrength = strength * alpha;

    for (const node of nodes) {
      if (node.type === 'honeypot') continue;
      // Skip nodes that are being dragged (have fixed positions)
      if (node.fx !== undefined && node.fx !== null) continue;

      // Apply repulsion from left boundary
      if (node.x < -halfWidth) {
        node.vx = (node.vx || 0) + (-halfWidth - node.x) * effectiveStrength;
      }
      // Apply repulsion from right boundary
      else if (node.x > halfWidth) {
        node.vx = (node.vx || 0) + (halfWidth - node.x) * effectiveStrength;
      }

      // Apply repulsion from top boundary
      if (node.y < -halfHeight) {
        node.vy = (node.vy || 0) + (-halfHeight - node.y) * effectiveStrength;
      }
      // Apply repulsion from bottom boundary
      else if (node.y > halfHeight) {
        node.vy = (node.vy || 0) + (halfHeight - node.y) * effectiveStrength;
      }
    }
  };

  force.initialize = (n: GraphNode[]) => {
    nodes = n;
  };

  return force;
};

export const useForceSimulation = ({
  nodesRef,
  width,
  height,
  projection,
}: UseForceSimulationProps) => {
  const simulationRef = useRef<d3.Simulation<GraphNode, undefined> | null>(null);

  // Consolidate initialization and updates to manage references correctly
  useEffect(() => {
    if (!simulationRef.current) {
      simulationRef.current = d3
        .forceSimulation<GraphNode>()
        .force('charge', d3.forceManyBody().strength(-300)) // Stronger repulsion
        .alphaDecay(0.015)
        .velocityDecay(0.4)
        .stop();
    }

    if (!projection || width === 0 || height === 0) return;

    const centerX = width / 2;
    const centerY = height / 2;
    const sim = simulationRef.current;

    // 2. Update Forces with clamped targets
    sim
      .force(
        'x',
        d3
          .forceX<GraphNode>((d) => {
            if (d.type === 'honeypot') return 0;

            // Handle Localhost / Unknown specifically
            if (!d.country_code || d.country_code === 'unknown' || d.country_code === 'local') {
              // Orbit around center (X axis), clamped to safe bounds
              const angle = (parseInt(d.id.slice(-4), 16) || 0) % 360;
              const targetX = Math.cos(angle * (Math.PI / 180)) * 280;
              return clampToBounds(targetX, centerX);
            }

            const coords = getCountryCoordinates(d.country_code);
            if (coords) {
              const p = projection([coords.lng, coords.lat]);
              const jitter = ((parseInt(d.id.slice(-2), 16) || 0) % 30) - 15;
              if (p) {
                const targetX = p[0] - centerX + jitter;
                // Clamp to safe bounds to prevent nodes from going out of view
                return clampToBounds(targetX, centerX);
              }
            }
            return 0; // fallback
          })
          .strength((d) =>
            d.country_code && d.country_code !== 'unknown' && d.country_code !== 'local'
              ? 0.7 // Reduced from 0.9 to allow boundary force to work
              : 0.05
          )
      )
      .force(
        'y',
        d3
          .forceY<GraphNode>((d) => {
            if (d.type === 'honeypot') return 0; // Will be fixed by tick()

            if (!d.country_code || d.country_code === 'unknown' || d.country_code === 'local') {
              const angle = (parseInt(d.id.slice(-4), 16) || 0) % 360;
              const VISUAL_OFFSET_Y = 120;
              const targetY = Math.sin(angle * (Math.PI / 180)) * 280 - VISUAL_OFFSET_Y;
              return clampToBounds(targetY, centerY);
            }

            const coords = getCountryCoordinates(d.country_code);
            if (coords) {
              const p = projection([coords.lng, coords.lat]);
              const jitter = ((parseInt(d.id.slice(-2), 16) || 0) % 30) - 15;
              if (p) {
                const targetY = p[1] - centerY + jitter;
                // Clamp to safe bounds to prevent nodes from going out of view
                return clampToBounds(targetY, centerY);
              }
            }
            return 0;
          })
          .strength((d) =>
            d.country_code && d.country_code !== 'unknown' && d.country_code !== 'local'
              ? 0.7 // Reduced from 0.9 to allow boundary force to work
              : 0.05
          )
      )
      .force(
        'collide',
        d3
          .forceCollide()
          .radius((d: any) => (d.type === 'honeypot' ? 70 : 35))
          .strength(1)
          .iterations(4)
      )
      // Add custom bounding box force to actively keep nodes within visible area
      .force('bounds', forceBoundingBox(width, height, BOUNDARY_PADDING, 0.8));

    // 3. Restart to apply new forces
    sim.alpha(1).restart();

    // Warm up the simulation to distribute nodes initially
    // This prevents them from starting clustered at (0,0)
    sim.tick();
    sim.tick();
    sim.tick();

    // Cleanup on unmount only
    return () => {
      // simulation stop isn't strictly necessary for ref-based singletons but good practice if hook re-runs drastically
      // Here we just keep the ref alive.
    };
  }, [width, height, projection]);

  const tick = useCallback(() => {
    if (!simulationRef.current) return;

    const nodes = Array.from(nodesRef.current.values());

    // Update simulation nodes
    simulationRef.current.nodes(nodes);

    // Tick one step
    simulationRef.current.tick();

    // Constrain honeypot to Milan, Italy
    // Milan Coordinates: 45.4642° N, 9.1900° E
    const MILAN_COORDS: [number, number] = [9.19, 45.4642]; // [Lon, Lat]

    // Default center if projection fails
    let honeypotX = 0;
    // Offset Y upward by 80px to account for the attack origins overlay at bottom
    let honeypotY = -80;

    if (projection) {
      const p = projection(MILAN_COORDS);
      if (p) {
        // Project relative to center
        const centerX = width / 2;
        const centerY = height / 2;
        honeypotX = p[0] - centerX;
        honeypotY = p[1] - centerY;
      }
    }

    // Calculate safe bounds
    const safeHalfWidth = width / 2 - BOUNDARY_PADDING;
    const safeHalfHeight = height / 2 - BOUNDARY_PADDING;

    nodes.forEach((node) => {
      if (node.type === 'honeypot') {
        node.x = honeypotX;
        node.y = honeypotY;
        node.vx = 0;
        node.vy = 0;
      } else {
        // Hard clamp attacker nodes to canvas boundaries as safety net
        // The bounding box force should handle most cases, this is a backup
        node.x = Math.max(-safeHalfWidth, Math.min(safeHalfWidth, node.x));
        node.y = Math.max(-safeHalfHeight, Math.min(safeHalfHeight, node.y));
      }
    });
  }, [nodesRef, projection, width, height]);

  /**
   * Manually redistribute nodes/restart simulation
   */
  const redistribute = useCallback(() => {
    if (!simulationRef.current) return;

    // High alpha to "heat up" the simulation
    simulationRef.current.alpha(1).restart();

    // Run a few ticks synchronously to spread them out immediately
    for (let i = 0; i < 10; i++) {
      simulationRef.current.tick();
    }
  }, []);

  /**
   * Start dragging a node - fixes its position and reheats simulation
   */
  const startDrag = useCallback((node: GraphNode) => {
    if (!simulationRef.current || node.type === 'honeypot') return;

    // Reheat the simulation
    simulationRef.current.alphaTarget(0.3).restart();

    // Fix the node position
    node.fx = node.x;
    node.fy = node.y;
  }, []);

  /**
   * Update dragged node position with boundary constraints
   */
  const updateDrag = useCallback(
    (node: GraphNode, x: number, y: number) => {
      if (node.type === 'honeypot') return;

      // Clamp position to safe bounds during drag
      const safeHalfWidth = width / 2 - BOUNDARY_PADDING;
      const safeHalfHeight = height / 2 - BOUNDARY_PADDING;
      const clampedX = Math.max(-safeHalfWidth, Math.min(safeHalfWidth, x));
      const clampedY = Math.max(-safeHalfHeight, Math.min(safeHalfHeight, y));

      node.fx = clampedX;
      node.fy = clampedY;
      node.x = clampedX;
      node.y = clampedY;
    },
    [width, height]
  );

  /**
   * End drag - release the node and let physics resume
   */
  const endDrag = useCallback((node: GraphNode, keepPosition = false) => {
    if (!simulationRef.current) return;

    // Cool down the simulation
    simulationRef.current.alphaTarget(0);

    if (!keepPosition) {
      // Release node to physics
      node.fx = null;
      node.fy = null;
    }
  }, []);

  return {
    simulation: simulationRef.current,
    tick,
    redistribute,
    startDrag,
    updateDrag,
    endDrag,
  };
};
