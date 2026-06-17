/**
 * ClusterGraph V2 - Network graph visualization for botnet clusters
 *
 * Uses react-force-graph-2d for better performance and interactivity.
 * Visualizes C2 hubs and bot nodes to identify the "heart" of the botnet.
 */

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import type { ForceGraphMethods } from 'react-force-graph-2d';
import * as d3 from 'd3';
import { ZoomIn, ZoomOut, Target, Download, Maximize } from 'lucide-react';
import {
  exportToPNG,
  exportToSVG,
  exportToJSON,
  getTimestampedFilename,
} from '../utils/graphExport';
import type { ClusterGraphProps, Node } from './types';
import { buildClusterGraphData } from './graphBuilder';

export function ClusterGraphV2({ clusters, hubNodes }: ClusterGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<ForceGraphMethods>();
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [hoveredNode, setHoveredNode] = useState<Node | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  // Build graph data from clusters and hubs
  const graphData = useMemo(() => buildClusterGraphData(clusters, hubNodes), [clusters, hubNodes]);

  // Container resize observer
  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  // Configure physics forces
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;

    // Repulsion between nodes
    fg.d3Force('charge')?.strength(-300);

    // Link distance
    fg.d3Force('link')?.distance((link: any) => {
      return link.strength === 1.0 ? 100 : 80;
    });

    // Collision detection
    fg.d3Force('collide', d3.forceCollide((node: any) => node.size + 5).strength(0.7));

    // Center force
    fg.d3Force('center')?.strength(0.5);

    // Warm up simulation
    fg.d3ReheatSimulation();
  }, []);

  // Initial fit-to-view after graph stabilizes
  useEffect(() => {
    if (dimensions.width > 0 && !isInitialized) {
      const timer = setTimeout(() => {
        fgRef.current?.zoomToFit(400, 80);
        setIsInitialized(true);
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [dimensions, isInitialized]);

  // Graph controls
  const handleZoomIn = () => {
    const currentZoom = fgRef.current?.zoom() || 1;
    fgRef.current?.zoom(currentZoom * 1.5, 300);
  };

  const handleZoomOut = () => {
    const currentZoom = fgRef.current?.zoom() || 1;
    fgRef.current?.zoom(currentZoom / 1.5, 300);
  };

  const handleFitView = () => {
    fgRef.current?.zoomToFit(400, 80);
  };

  const handleRecenter = () => {
    fgRef.current?.centerAt(0, 0, 300);
    fgRef.current?.zoom(1, 300);
  };

  const handleNodeClick = (node: any) => {
    setSelectedNode(node as Node);
    fgRef.current?.centerAt(node.x as number, node.y as number, 500);
    fgRef.current?.zoom(3, 500);
  };

  const handleBackgroundClick = () => {
    setSelectedNode(null);
  };

  const handleNodeHover = useCallback((node: any) => {
    setHoveredNode(node as Node | null);
    if (containerRef.current) {
      containerRef.current.style.cursor = node ? 'pointer' : 'grab';
    }
  }, []);

  // Export handlers
  const handleExportPNG = async () => {
    // Get canvas from ForceGraph
    const canvas = containerRef.current?.querySelector('canvas');
    if (!canvas) return;

    try {
      const filename = getTimestampedFilename('cluster-graph', 'png');
      await exportToPNG(canvas as HTMLCanvasElement, filename);
    } catch (error) {
      console.error('Failed to export PNG:', error);
      alert('Failed to export PNG. See console for details.');
    }
  };

  const handleExportSVG = () => {
    // Get canvas for dimensions
    const canvas = containerRef.current?.querySelector('canvas');
    if (!canvas) return;

    try {
      const filename = getTimestampedFilename('cluster-graph', 'svg');
      const zoom = fgRef.current?.zoom() || 1;
      const center = fgRef.current?.centerAt();
      const pan = center ? { x: center.x || 0, y: center.y || 0 } : { x: 0, y: 0 };

      exportToSVG(
        { nodes: graphData.nodes as any, edges: graphData.links as any },
        canvas.width,
        canvas.height,
        zoom,
        pan,
        filename
      );
    } catch (error) {
      console.error('Failed to export SVG:', error);
      alert('Failed to export SVG. See console for details.');
    }
  };

  const handleExportJSON = () => {
    try {
      const filename = getTimestampedFilename('cluster-graph-data', 'json');
      exportToJSON({ nodes: graphData.nodes as any, edges: graphData.links as any }, filename);
    } catch (error) {
      console.error('Failed to export JSON:', error);
      alert('Failed to export JSON. See console for details.');
    }
  };

  // Custom node rendering
  const paintNode = useCallback(
    (node: any, ctx: CanvasRenderingContext2D) => {
      const { x = 0, y = 0, size = 5, type, color = '#666' } = node;
      const isSelected = selectedNode?.id === node.id;
      const isHovered = hoveredNode?.id === node.id;

      // Hub nodes: Hexagon
      if (type === 'hub') {
        const sides = 6;
        const angleStep = (Math.PI * 2) / sides;

        ctx.beginPath();
        for (let i = 0; i < sides; i++) {
          const angle = i * angleStep - Math.PI / 2;
          const px = x + Math.cos(angle) * size;
          const py = y + Math.sin(angle) * size;
          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.closePath();

        ctx.fillStyle = color;
        ctx.fill();

        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Icon
        ctx.fillStyle = '#ffffff';
        ctx.font = `bold ${Math.max(10, size * 0.5)}px Arial`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('⚡', x, y);
      } else if (type === 'cluster') {
        // Cluster nodes: Square
        ctx.beginPath();
        ctx.rect(x - size, y - size, size * 2, size * 2);
        ctx.fillStyle = color;
        ctx.fill();

        ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.lineWidth = 2;
        ctx.stroke();
      } else {
        // Bot nodes: Circle
        ctx.beginPath();
        ctx.arc(x, y, size, 0, 2 * Math.PI);
        ctx.fillStyle = color;
        ctx.fill();

        ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // Selection ring
      if (isSelected || isHovered) {
        ctx.beginPath();
        if (type === 'cluster') {
          ctx.rect(x - size - 4, y - size - 4, (size + 4) * 2, (size + 4) * 2);
        } else {
          ctx.arc(x, y, size + 4, 0, 2 * Math.PI);
        }
        ctx.strokeStyle = isSelected ? '#00ffff' : '#ffffff';
        ctx.lineWidth = isSelected ? 3 : 2;
        ctx.stroke();
      }

      // Label for hubs and clusters
      if (type === 'hub' || type === 'cluster' || isSelected) {
        ctx.fillStyle = '#fff';
        ctx.font = `11px monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        const label = node.label.length > 15 ? node.label.slice(0, 12) + '...' : node.label;
        ctx.fillText(label, x, y + size + 5);
      }
    },
    [selectedNode, hoveredNode]
  );

  // Custom link rendering
  const paintLink = useCallback((link: any, ctx: CanvasRenderingContext2D) => {
    const { source, target, strength, color } = link;
    const sx = source.x || 0;
    const sy = source.y || 0;
    const tx = target.x || 0;
    const ty = target.y || 0;

    ctx.beginPath();
    ctx.moveTo(sx, sy);
    ctx.lineTo(tx, ty);
    ctx.strokeStyle = color || `rgba(255, 255, 255, ${strength * 0.3})`;
    ctx.lineWidth = strength * 2;
    ctx.stroke();
  }, []);

  // Define clickable area for nodes (for drag & click interaction)
  const nodePointerAreaPaint = useCallback(
    (node: any, color: string, ctx: CanvasRenderingContext2D) => {
      const { x = 0, y = 0, size = 5, type } = node;

      ctx.fillStyle = color;

      if (type === 'cluster') {
        // Square clickable area for cluster nodes
        ctx.fillRect(x - size, y - size, size * 2, size * 2);
      } else {
        // Circular clickable area for hub and bot nodes
        ctx.beginPath();
        ctx.arc(x, y, size, 0, 2 * Math.PI);
        ctx.fill();
      }
    },
    []
  );

  return (
    <div className="cluster-graph-container" ref={containerRef}>
      {/* Controls */}
      <div className="cluster-graph-controls">
        <button onClick={handleZoomIn} title="Zoom in">
          <ZoomIn size={16} />
        </button>
        <button onClick={handleZoomOut} title="Zoom out">
          <ZoomOut size={16} />
        </button>
        <button onClick={handleFitView} title="Fit to view">
          <Maximize size={16} />
        </button>
        <button onClick={handleRecenter} title="Reset view">
          <Target size={16} />
        </button>
        <div className="cluster-graph-controls-divider" />
        <div className="cluster-graph-export-dropdown">
          <button className="cluster-graph-export-btn" title="Export graph">
            <Download size={16} />
            Export
          </button>
          <div className="cluster-graph-export-menu">
            <button onClick={handleExportPNG}>
              <Download size={14} />
              Export as PNG
            </button>
            <button onClick={handleExportSVG}>
              <Download size={14} />
              Export as SVG
            </button>
            <button onClick={handleExportJSON}>
              <Download size={14} />
              Export Data (JSON)
            </button>
          </div>
        </div>
      </div>

      {/* ForceGraph */}
      <ForceGraph2D
        ref={fgRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={graphData}
        nodeCanvasObject={paintNode}
        nodePointerAreaPaint={nodePointerAreaPaint}
        linkCanvasObject={paintLink}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        onNodeDrag={(node) => {
          // Update node position during drag
          node.fx = node.x;
          node.fy = node.y;
        }}
        onNodeDragEnd={(node) => {
          // Release fixed position after drag ends
          node.fx = undefined;
          node.fy = undefined;
        }}
        onBackgroundClick={handleBackgroundClick}
        nodeRelSize={1}
        enableNodeDrag={true}
        enableZoomInteraction={true}
        enablePanInteraction={true}
        cooldownTicks={100}
        warmupTicks={50}
      />

      {/* Legend */}
      <div className="cluster-graph-legend">
        <div className="cluster-graph-legend-item">
          <div className="cluster-graph-legend-dot hub" />
          <span>C2 Hub (Critical)</span>
        </div>
        <div className="cluster-graph-legend-item">
          <div className="cluster-graph-legend-dot cluster" />
          <span>Cluster Center</span>
        </div>
        <div className="cluster-graph-legend-item">
          <div className="cluster-graph-legend-dot bot" />
          <span>Bot Node</span>
        </div>
      </div>

      {/* Node Details */}
      {selectedNode && (
        <div className="cluster-graph-details">
          <div className="cluster-graph-details-header">
            <h4>{selectedNode.type.toUpperCase()}</h4>
            <button onClick={() => setSelectedNode(null)}>×</button>
          </div>
          <div className="cluster-graph-details-content">
            <div className="cluster-graph-detail-row">
              <span>ID:</span>
              <span className="mono">{selectedNode.label}</span>
            </div>
            {selectedNode.centrality !== undefined && (
              <div className="cluster-graph-detail-row">
                <span>Centrality:</span>
                <span>{(selectedNode.centrality * 100).toFixed(1)}%</span>
              </div>
            )}
            {selectedNode.cluster && (
              <div className="cluster-graph-detail-row">
                <span>Cluster:</span>
                <span className="mono">{selectedNode.cluster.slice(0, 8)}</span>
              </div>
            )}
            <div className="cluster-graph-detail-row">
              <span>Type:</span>
              <span className={`cluster-graph-type-badge ${selectedNode.type}`}>
                {selectedNode.type === 'hub'
                  ? '⚠️ C2 Server'
                  : selectedNode.type === 'cluster'
                    ? '🔵 Cluster'
                    : '🤖 Bot'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
