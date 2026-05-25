/**
 * ClusterGraph - Network graph visualization for botnet clusters
 *
 * Visualizes C2 hubs and bot nodes to identify the "heart" of the botnet.
 * Uses force-directed graph layout simulation.
 */

import { useEffect, useRef, useState } from 'react';
import { ZoomIn, ZoomOut, Target, Download } from 'lucide-react';
import type { BotnetCluster, HubNode } from '../../../../../../types/discovery';
import {
  exportToPNG,
  exportToSVG,
  exportToJSON,
  getTimestampedFilename,
} from '../utils/graphExport';

interface Node {
  id: string;
  type: 'hub' | 'bot' | 'cluster';
  label: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  cluster?: string;
  centrality?: number;
}

interface Edge {
  source: string;
  target: string;
  strength: number;
}

interface ClusterGraphProps {
  clusters: BotnetCluster[];
  hubNodes: HubNode[];
}

export function ClusterGraph({ clusters, hubNodes }: ClusterGraphProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [hoveredNode, setHoveredNode] = useState<Node | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const animationFrameRef = useRef<number>();

  // Build graph data from clusters and hubs
  const buildGraphData = (): { nodes: Node[]; edges: Edge[] } => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];

    // Add hub nodes (C2 servers)
    hubNodes.forEach((hub, i) => {
      nodes.push({
        id: hub.ip,
        type: 'hub',
        label: hub.ip,
        x: Math.cos((i * 2 * Math.PI) / hubNodes.length) * 150,
        y: Math.sin((i * 2 * Math.PI) / hubNodes.length) * 150,
        vx: 0,
        vy: 0,
        size: Math.sqrt(hub.degree_centrality * 1000) + 15,
        centrality: hub.degree_centrality,
      });
    });

    // Add cluster nodes and bots
    clusters.forEach((cluster, clusterIdx) => {
      const clusterCenter = {
        x: Math.cos((clusterIdx * 2 * Math.PI) / clusters.length) * 200,
        y: Math.sin((clusterIdx * 2 * Math.PI) / clusters.length) * 200,
      };

      // Add cluster center node
      nodes.push({
        id: `cluster-${cluster.cluster_id}`,
        type: 'cluster',
        label: `Cluster ${cluster.cluster_id.slice(0, 6)}`,
        x: clusterCenter.x,
        y: clusterCenter.y,
        vx: 0,
        vy: 0,
        size: Math.sqrt(cluster.size) * 8 + 10,
        cluster: cluster.cluster_id,
      });

      // Add bot nodes (sample up to 10 per cluster for performance)
      const sampleSize = Math.min(10, cluster.member_ips.length);
      cluster.member_ips.slice(0, sampleSize).forEach((ip, i) => {
        const angle = (i * 2 * Math.PI) / sampleSize;
        const radius = 80;
        nodes.push({
          id: ip,
          type: 'bot',
          label: ip,
          x: clusterCenter.x + Math.cos(angle) * radius,
          y: clusterCenter.y + Math.sin(angle) * radius,
          vx: 0,
          vy: 0,
          size: 6,
          cluster: cluster.cluster_id,
        });

        // Connect bot to cluster center
        edges.push({
          source: ip,
          target: `cluster-${cluster.cluster_id}`,
          strength: 0.5,
        });
      });

      // Connect cluster to its suspected C2
      if (cluster.suspected_cc_ip) {
        edges.push({
          source: `cluster-${cluster.cluster_id}`,
          target: cluster.suspected_cc_ip,
          strength: 1.0,
        });
      }

      // Connect to associated C2s
      cluster.associated_cc_ips?.forEach((ccIP) => {
        edges.push({
          source: `cluster-${cluster.cluster_id}`,
          target: ccIP,
          strength: 0.7,
        });
      });
    });

    return { nodes, edges };
  };

  const [graphData, setGraphData] = useState(() => buildGraphData());

  useEffect(() => {
    setGraphData(buildGraphData());
  }, [clusters, hubNodes]);

  // Force-directed layout simulation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;

    let nodes = [...graphData.nodes];
    const edges = graphData.edges;

    // Simple force simulation
    const simulate = () => {
      // Apply forces
      nodes.forEach((node) => {
        // Gravity towards center
        const dx = centerX / zoom - node.x;
        const dy = centerY / zoom - node.y;
        const distToCenter = Math.sqrt(dx * dx + dy * dy);
        if (distToCenter > 0) {
          node.vx += (dx / distToCenter) * 0.01;
          node.vy += (dy / distToCenter) * 0.01;
        }

        // Repulsion between nodes
        nodes.forEach((other) => {
          if (node.id === other.id) return;
          const dx = other.x - node.x;
          const dy = other.y - node.y;
          const dist = Math.sqrt(dx * dx + dy * dy) + 0.1;
          const force = ((node.size + other.size) / (dist * dist)) * 10;
          node.vx -= (dx / dist) * force;
          node.vy -= (dy / dist) * force;
        });
      });

      // Apply edge forces (spring)
      edges.forEach((edge) => {
        const source = nodes.find((n) => n.id === edge.source);
        const target = nodes.find((n) => n.id === edge.target);
        if (!source || !target) return;

        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const dist = Math.sqrt(dx * dx + dy * dy) + 0.1;
        const force = (dist - 100) * edge.strength * 0.01;

        source.vx += (dx / dist) * force;
        source.vy += (dy / dist) * force;
        target.vx -= (dx / dist) * force;
        target.vy -= (dy / dist) * force;
      });

      // Update positions with damping
      nodes.forEach((node) => {
        node.x += node.vx;
        node.y += node.vy;
        node.vx *= 0.85;
        node.vy *= 0.85;
      });
    };

    // Render function
    const render = () => {
      ctx.clearRect(0, 0, width, height);
      ctx.save();

      // Apply zoom and pan
      ctx.translate(width / 2 + pan.x, height / 2 + pan.y);
      ctx.scale(zoom, zoom);
      ctx.translate(-width / 2, -height / 2);

      // Draw edges
      ctx.strokeStyle = 'rgba(0, 255, 255, 0.15)';
      ctx.lineWidth = 1;
      edges.forEach((edge) => {
        const source = nodes.find((n) => n.id === edge.source);
        const target = nodes.find((n) => n.id === edge.target);
        if (!source || !target) return;

        const alpha = edge.strength * 0.3;
        ctx.strokeStyle = `rgba(0, 255, 255, ${alpha})`;
        ctx.lineWidth = edge.strength * 2;
        ctx.beginPath();
        ctx.moveTo(source.x, source.y);
        ctx.lineTo(target.x, target.y);
        ctx.stroke();
      });

      // Draw nodes
      nodes.forEach((node) => {
        // Determine color
        let fillColor = 'rgba(100, 100, 100, 0.8)';
        let strokeColor = 'rgba(255, 255, 255, 0.3)';

        if (node.type === 'hub') {
          fillColor = 'rgba(255, 71, 87, 0.9)';
          strokeColor = 'rgba(255, 71, 87, 1)';
        } else if (node.type === 'cluster') {
          fillColor = 'rgba(168, 85, 247, 0.8)';
          strokeColor = 'rgba(168, 85, 247, 1)';
        } else if (node.type === 'bot') {
          fillColor = 'rgba(0, 255, 255, 0.6)';
          strokeColor = 'rgba(0, 255, 255, 0.8)';
        }

        // Highlight selected/hovered
        if (selectedNode?.id === node.id || hoveredNode?.id === node.id) {
          strokeColor = '#fff';
          ctx.lineWidth = 3;
        } else {
          ctx.lineWidth = 2;
        }

        // Draw node circle
        ctx.fillStyle = fillColor;
        ctx.strokeStyle = strokeColor;
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.size, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();

        // Draw label for hubs and clusters
        if (node.type === 'hub' || node.type === 'cluster' || selectedNode?.id === node.id) {
          ctx.fillStyle = '#fff';
          ctx.font = '11px monospace';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'top';
          ctx.fillText(
            node.label.length > 15 ? node.label.slice(0, 12) + '...' : node.label,
            node.x,
            node.y + node.size + 5
          );
        }
      });

      ctx.restore();
    };

    // Animation loop
    const animate = () => {
      simulate();
      render();
      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [graphData, zoom, pan, selectedNode, hoveredNode]);

  // Mouse interaction handlers
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left - canvas.width / 2 - pan.x) / zoom + canvas.width / 2;
    const y = (e.clientY - rect.top - canvas.height / 2 - pan.y) / zoom + canvas.height / 2;

    if (isDragging) {
      setPan({
        x: pan.x + (e.clientX - dragStart.x),
        y: pan.y + (e.clientY - dragStart.y),
      });
      setDragStart({ x: e.clientX, y: e.clientY });
      return;
    }

    // Check for node hover
    const hoveredNode = graphData.nodes.find((node) => {
      const dx = node.x - x;
      const dy = node.y - y;
      return Math.sqrt(dx * dx + dy * dy) < node.size;
    });

    setHoveredNode(hoveredNode || null);
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isDragging) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left - canvas.width / 2 - pan.x) / zoom + canvas.width / 2;
    const y = (e.clientY - rect.top - canvas.height / 2 - pan.y) / zoom + canvas.height / 2;

    const clickedNode = graphData.nodes.find((node) => {
      const dx = node.x - x;
      const dy = node.y - y;
      return Math.sqrt(dx * dx + dy * dy) < node.size;
    });

    setSelectedNode(clickedNode || null);
  };

  const handleZoomIn = () => setZoom(Math.min(zoom * 1.2, 3));
  const handleZoomOut = () => setZoom(Math.max(zoom / 1.2, 0.3));
  const handleReset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setSelectedNode(null);
  };

  // Export handlers
  const handleExportPNG = async () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    try {
      const filename = getTimestampedFilename('cluster-graph', 'png');
      await exportToPNG(canvas, filename);
    } catch (error) {
      console.error('Failed to export PNG:', error);
      alert('Failed to export PNG. See console for details.');
    }
  };

  const handleExportSVG = () => {
    try {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const filename = getTimestampedFilename('cluster-graph', 'svg');
      exportToSVG(graphData, canvas.width, canvas.height, zoom, pan, filename);
    } catch (error) {
      console.error('Failed to export SVG:', error);
      alert('Failed to export SVG. See console for details.');
    }
  };

  const handleExportJSON = () => {
    try {
      const filename = getTimestampedFilename('cluster-graph-data', 'json');
      exportToJSON(graphData, filename);
    } catch (error) {
      console.error('Failed to export JSON:', error);
      alert('Failed to export JSON. See console for details.');
    }
  };

  return (
    <div className="cluster-graph-container">
      <div className="cluster-graph-controls">
        <button onClick={handleZoomIn} title="Zoom in">
          <ZoomIn size={16} />
        </button>
        <button onClick={handleZoomOut} title="Zoom out">
          <ZoomOut size={16} />
        </button>
        <button onClick={handleReset} title="Reset view">
          <Target size={16} />
        </button>
        <span className="cluster-graph-zoom-level">{(zoom * 100).toFixed(0)}%</span>
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

      <canvas
        ref={canvasRef}
        width={800}
        height={500}
        className="cluster-graph-canvas"
        onMouseMove={handleMouseMove}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onClick={handleClick}
        style={{ cursor: isDragging ? 'grabbing' : hoveredNode ? 'pointer' : 'grab' }}
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
