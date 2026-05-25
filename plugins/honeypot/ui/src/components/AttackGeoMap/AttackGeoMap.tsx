/**
 * AttackGeoMap - Interactive Force-Directed Attack Visualization
 *
 * A network graph showing attackers connected to the honeypot.
 * Refactored into modular structure with separate renderers and components.
 *
 * Features drag-and-drop interaction for repositioning attacker nodes.
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import html2canvas from 'html2canvas';
import './AttackGeoMap.css';
import { getThreatLevel, type ThreatLevel } from '../geoUtils';
import { useAttackStream } from '../hooks/useAttackStream';
import { useForceSimulation } from '../hooks/useForceSimulation';
import { useWorldMapProjection } from '../hooks/useWorldMapProjection';
import { GraphNode } from '../types';
import { AttackGraphProps } from './types';
import { NODE_DIMENSIONS } from './constants';

// Renderers
import { drawGrid, drawWorldMap, drawRadarSweep, drawEdges, drawNodes } from './renderers';

// UI Components
import { GeoMapHeader, GeoMapLegend, NodeTooltip, NodeDetailModal } from './components';

const AttackGeoMap: React.FC<AttackGraphProps> = ({
  activeProtocols = [],
  events = [],
  attackers = [],
  onSelectNode,
  isActive = true,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [draggingNode, setDraggingNode] = useState<GraphNode | null>(null);
  const [threatLevel, setThreatLevel] = useState<ThreatLevel>(1);
  const [isCapturing, setIsCapturing] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Track isActive in a ref for use in animation loop
  const isActiveRef = useRef(isActive);
  useEffect(() => {
    isActiveRef.current = isActive;
  }, [isActive]);

  // Data Layer Hook - now includes attackers for persistent nodes
  const { nodesRef, edgesRef, stats, isConnected, attackVelocity } = useAttackStream({
    activeProtocols,
    events,
    attackers,
  });

  // Map Projection
  const { projection } = useWorldMapProjection(dimensions.width, dimensions.height);

  // Physics Layer Hook with drag support
  const { tick, startDrag, updateDrag, endDrag, redistribute } = useForceSimulation({
    nodesRef,
    width: dimensions.width,
    height: dimensions.height,
    projection,
  });

  // Update threat level based on velocity
  useEffect(() => {
    setThreatLevel(getThreatLevel(attackVelocity));
  }, [attackVelocity]);

  // Auto-distribute when nodes structure changes significantly (e.g. initial load or honeypot switch)
  useEffect(() => {
    if (nodesRef.current.size > 0) {
      redistribute();
    }
  }, [nodesRef.current.size, redistribute]); // Rerun when node count changes

  // Handle Resize
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current && canvasRef.current) {
        const width = containerRef.current.clientWidth;
        const height = containerRef.current.clientHeight;
        canvasRef.current.width = width;
        canvasRef.current.height = height;
        setDimensions({ width, height });
      }
    };

    const resizeObserver = new ResizeObserver(handleResize);
    if (containerRef.current) resizeObserver.observe(containerRef.current);
    handleResize();

    return () => resizeObserver.disconnect();
  }, []);

  // Helper to find node at position
  const findNodeAtPos = useCallback(
    (x: number, y: number): GraphNode | null => {
      for (const node of nodesRef.current.values()) {
        const dx = node.x - x;
        const dy = node.y - y;
        const hitRadius =
          node.type === 'honeypot'
            ? node.radius
            : node.radius + NODE_DIMENSIONS.ATTACKER_HIT_PADDING;
        if (Math.sqrt(dx * dx + dy * dy) < hitRadius) {
          return node;
        }
      }
      return null;
    },
    [nodesRef]
  );

  // Mouse handlers with proper drag vs click separation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Drag state tracking
    let isDragging = false;
    let hasDraggedSignificantly = false;
    let dragStartPos = { x: 0, y: 0 };
    let currentDragNode: GraphNode | null = null;
    const DRAG_THRESHOLD = 5; // Pixels before considered a drag

    const getMousePos = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      return {
        x: e.clientX - rect.left - centerX,
        y: e.clientY - rect.top - centerY,
        clientX: e.clientX,
        clientY: e.clientY,
      };
    };

    const handleMouseDown = (e: MouseEvent) => {
      const pos = getMousePos(e);
      const node = findNodeAtPos(pos.x, pos.y);

      if (node && node.type === 'attacker') {
        e.preventDefault();
        isDragging = true;
        hasDraggedSignificantly = false;
        dragStartPos = { x: pos.clientX, y: pos.clientY };
        currentDragNode = node;
        startDrag(node);
        setDraggingNode(node);
      }
    };

    const handleMouseMove = (e: MouseEvent) => {
      const pos = getMousePos(e);

      if (isDragging && currentDragNode) {
        // Check if we've moved enough to consider it a drag
        const dx = pos.clientX - dragStartPos.x;
        const dy = pos.clientY - dragStartPos.y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance > DRAG_THRESHOLD) {
          hasDraggedSignificantly = true;
        }

        if (hasDraggedSignificantly) {
          updateDrag(currentDragNode, pos.x, pos.y);
          canvas.style.cursor = 'grabbing';
        }
        return;
      }

      // Handle hover when not dragging
      const hovered = findNodeAtPos(pos.x, pos.y);
      setHoveredNode(hovered);

      if (hovered) {
        canvas.style.cursor = hovered.type === 'attacker' ? 'grab' : 'pointer';
      } else {
        canvas.style.cursor = 'default';
      }
    };

    const handleMouseUp = (e: MouseEvent) => {
      const wasSignificantDrag = hasDraggedSignificantly;

      if (currentDragNode) {
        endDrag(currentDragNode, true);
      }

      // If it was just a click (no significant drag), handle selection
      if (!wasSignificantDrag && isDragging && currentDragNode) {
        const pos = getMousePos(e);
        const clicked = findNodeAtPos(pos.x, pos.y);
        if (clicked && clicked.type === 'attacker') {
          setSelectedNode(clicked);
        }
      } else if (!isDragging) {
        // Click on canvas when not starting a drag
        const pos = getMousePos(e);
        const clicked = findNodeAtPos(pos.x, pos.y);
        if (clicked) {
          setSelectedNode(clicked);
        } else {
          // Close modal on click outside
          setSelectedNode(null);
        }
      }

      // Reset drag state
      isDragging = false;
      hasDraggedSignificantly = false;
      currentDragNode = null;
      setDraggingNode(null);
      canvas.style.cursor = 'default';
    };

    const handleMouseLeave = () => {
      if (currentDragNode) {
        endDrag(currentDragNode, true);
      }
      isDragging = false;
      hasDraggedSignificantly = false;
      currentDragNode = null;
      setDraggingNode(null);
      setHoveredNode(null);
      canvas.style.cursor = 'default';
    };

    canvas.addEventListener('mousedown', handleMouseDown);
    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('mouseup', handleMouseUp);
    canvas.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      canvas.removeEventListener('mousedown', handleMouseDown);
      canvas.removeEventListener('mousemove', handleMouseMove);
      canvas.removeEventListener('mouseup', handleMouseUp);
      canvas.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [nodesRef, findNodeAtPos, startDrag, updateDrag, endDrag]);

  // Render Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;

    let animId: number;

    const animate = (t: number) => {
      // Skip heavy rendering when component is not active (tab not visible)
      if (!isActiveRef.current) {
        animId = requestAnimationFrame(animate);
        return;
      }

      const time = t / 1000;
      const width = canvas.width;
      const height = canvas.height;
      const centerX = width / 2;
      const centerY = height / 2;

      // Clear
      ctx.clearRect(0, 0, width, height);

      // Physics Step
      tick();

      // Find honeypot node position
      const honeypotNode = nodesRef.current.get('honeypot');
      const honeypotPosition = honeypotNode
        ? { x: centerX + honeypotNode.x, y: centerY + honeypotNode.y }
        : undefined;

      // Create render context
      const renderContext = { ctx, width, height, centerX, centerY, time, honeypotPosition };

      // 1. Draw Background Layers
      drawGrid(renderContext);
      drawWorldMap({ ...renderContext, projection });
      drawRadarSweep(renderContext);

      // 2. Draw Edges
      drawEdges({
        ...renderContext,
        edges: edgesRef.current,
        nodes: nodesRef.current,
      });

      // 3. Draw Nodes
      drawNodes({
        ...renderContext,
        nodes: nodesRef.current,
        hoveredNodeId: hoveredNode?.id || null,
        selectedNodeId: selectedNode?.id || null,
        draggingNodeId: draggingNode?.id || null,
        threatLevel,
      });

      animId = requestAnimationFrame(animate);
    };

    animId = requestAnimationFrame(animate);

    return () => cancelAnimationFrame(animId);
  }, [threatLevel, hoveredNode, selectedNode, draggingNode, tick, edgesRef, nodesRef, projection]);

  // Screenshot capture handler
  const handleScreenshotCapture = useCallback(async () => {
    if (!containerRef.current || isCapturing) return;

    setIsCapturing(true);

    // Temporarily hide tooltips and modals for clean capture
    const previousSelectedNode = selectedNode;
    const previousHoveredNode = hoveredNode;
    setSelectedNode(null);
    setHoveredNode(null);

    // Add screenshot mode class to hide overlays (CRT, Vignette)
    containerRef.current.classList.add('screenshot-mode');

    // Wait for React to re-render without overlays
    await new Promise((resolve) => setTimeout(resolve, 100));

    try {
      const canvas = await html2canvas(containerRef.current, {
        backgroundColor: '#05080f', // Enforce solid background color
        scale: 2, // Higher resolution
        useCORS: true,
        logging: false,
        // Ignore CRT and vignette effect pseudo-elements for cleaner capture
        ignoreElements: (element: Element) => {
          return (
            element.classList?.contains('node-detail-popover') ||
            element.classList?.contains('geo-map-tooltip')
          );
        },
      });

      // Generate filename with timestamp
      const now = new Date();
      const dateStr = now.toISOString().slice(0, 16).replace('T', '_').replace(':', '-');
      const filename = `honeypot-globe-${dateStr}.png`;

      // Convert to blob and download
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
      // Restore previous state
      if (containerRef.current) {
        containerRef.current.classList.remove('screenshot-mode');
      }
      setSelectedNode(previousSelectedNode);
      setHoveredNode(previousHoveredNode);
      setIsCapturing(false);
    }
  }, [isCapturing, selectedNode, hoveredNode]);

  // Fullscreen toggle handler
  const handleToggleFullscreen = useCallback(() => {
    if (!containerRef.current) return;

    if (!isFullscreen) {
      // Enter fullscreen
      containerRef.current.requestFullscreen?.().catch((err) => {
        console.error('Failed to enter fullscreen:', err);
      });
    } else {
      // Exit fullscreen
      document.exitFullscreen?.().catch((err) => {
        console.error('Failed to exit fullscreen:', err);
      });
    }
  }, [isFullscreen]);

  // Listen for fullscreen changes (handles ESC key and browser controls)
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  return (
    <div className={`geo-map-container${isFullscreen ? ' fullscreen' : ''}`} ref={containerRef}>
      <GeoMapHeader
        stats={stats}
        isConnected={isConnected}
        threatLevel={threatLevel}
        attackVelocity={attackVelocity}
        onRedistribute={redistribute}
        onCapture={handleScreenshotCapture}
        isCapturing={isCapturing}
        isFullscreen={isFullscreen}
        onToggleFullscreen={handleToggleFullscreen}
      />

      <canvas ref={canvasRef} className="geo-map-canvas" />

      {selectedNode && (
        <NodeDetailModal
          ref={modalRef}
          node={selectedNode}
          nodePosition={{
            x: dimensions.width / 2 + selectedNode.x,
            y: dimensions.height / 2 + selectedNode.y,
          }}
          containerDimensions={dimensions}
          onClose={() => setSelectedNode(null)}
          onViewDetails={onSelectNode}
        />
      )}

      <GeoMapLegend activeProtocols={activeProtocols} />

      {hoveredNode && hoveredNode.type === 'attacker' && !selectedNode && !draggingNode && (
        <NodeTooltip node={hoveredNode} />
      )}
    </div>
  );
};

export default React.memo(AttackGeoMap);
