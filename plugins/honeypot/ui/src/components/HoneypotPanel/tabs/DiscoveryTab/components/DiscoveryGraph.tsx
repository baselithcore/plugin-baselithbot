import { useState, useRef, useMemo, useEffect, useCallback } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import * as d3 from 'd3';
import { DiscoveryDetailModal } from './DiscoveryDetailModal';
import { GraphControls } from './GraphControls';
import { GraphStats } from './GraphStats';
import { GraphLegend } from './GraphLegend';
import { NodeTooltip } from './NodeTooltip';
import type {
  DiscoveryResult,
  DiscoveryGraphNode,
  BotnetCluster,
  HubNode,
} from '../../../../types';
import { getNodeSize, getNodeColor, drawHexagon } from '../utils/graphHelpers';

import './DiscoveryGraph.css';

interface DiscoveryGraphProps {
  result: DiscoveryResult;
}

export function DiscoveryGraph({ result }: DiscoveryGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<ForceGraphMethods>();
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [selectedNode, setSelectedNode] = useState<DiscoveryGraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<DiscoveryGraphNode | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

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

  // Configure Physics Forces
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;

    // Increase repulsion (Charge) to space nodes out effectively
    fg.d3Force('charge')?.strength(-300);

    // Increase link distance
    fg.d3Force('link')?.distance(80);

    // Add collision force to prevent overlap
    // Radius = node size + padding (5px)
    fg.d3Force('collide', d3.forceCollide((node: any) => getNodeSize(node) + 5).strength(0.7));

    // Tweak centering force to be gentler so nodes can spread out
    fg.d3Force('center')?.strength(0.6);

    // Warm up the simulation
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

  // Transform data for the graph
  const graphData = useMemo(() => {
    if (!result.graph_data) return { nodes: [], links: [] };

    return {
      nodes: result.graph_data.nodes.map((n) => ({ ...n })),
      links: result.graph_data.edges.map((e) => ({
        source: e.source,
        target: e.target,
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        ...(({ source, target, ...rest }) => rest)(e),
      })),
    };
  }, [result]);

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

  const handleFocusHubs = () => {
    // Focus only on CONFIRMED C&C nodes, not potential ones
    const confirmedCC = graphData.nodes.filter((n: any) => n.is_hub && n.is_confirmed_cc);
    if (confirmedCC.length > 0) {
      const hub = confirmedCC[0] as any;
      fgRef.current?.centerAt(hub.x, hub.y, 500);
      fgRef.current?.zoom(3, 500);
    }
  };

  // Toggle fullscreen mode
  const handleToggleFullscreen = useCallback(() => {
    setIsFullscreen((prev) => !prev);
  }, []);

  // Handle Escape key to exit fullscreen
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false);
      }
    };

    if (isFullscreen) {
      document.addEventListener('keydown', handleKeyDown);
      // Prevent body scroll when fullscreen
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isFullscreen]);

  // Export to PNG
  const handleExportPNG = useCallback(() => {
    const canvas = containerRef.current?.querySelector('canvas');
    if (!canvas) return;

    const link = document.createElement('a');
    link.download = `network-topology-${new Date().toISOString().split('T')[0]}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  }, []);

  // Export to SVG
  const handleExportSVG = useCallback(() => {
    if (!graphData.nodes.length) return;

    const width = dimensions.width || 800;
    const height = dimensions.height || 600;

    // Create SVG element
    let svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`;

    // Background
    svgContent += `<rect width="100%" height="100%" fill="#0a1628"/>`;

    // Draw links
    graphData.links.forEach((link: any) => {
      const source =
        typeof link.source === 'object'
          ? link.source
          : graphData.nodes.find((n: any) => n.id === link.source);
      const target =
        typeof link.target === 'object'
          ? link.target
          : graphData.nodes.find((n: any) => n.id === link.target);
      if (source?.x && source?.y && target?.x && target?.y) {
        const color = link.is_intra_cluster
          ? 'rgba(46, 213, 115, 0.4)'
          : 'rgba(255, 255, 255, 0.15)';
        svgContent += `<line x1="${source.x + width / 2}" y1="${source.y + height / 2}" x2="${target.x + width / 2}" y2="${target.y + height / 2}" stroke="${color}" stroke-width="1"/>`;
      }
    });

    // Draw nodes
    graphData.nodes.forEach((node: any) => {
      const x = (node.x || 0) + width / 2;
      const y = (node.y || 0) + height / 2;
      const size = getNodeSize(node);
      const color = node.is_hub
        ? node.is_confirmed_cc
          ? '#ff4757'
          : '#ffaa00'
        : node.community_id !== undefined
          ? [
              '#2ed573',
              '#1e90ff',
              '#a55eea',
              '#ffa502',
              '#00d2d3',
              '#ff6b81',
              '#7bed9f',
              '#70a1ff',
            ][node.community_id % 8]
          : '#2ed573';

      if (node.is_hub) {
        // Hexagon for hubs
        const points = [];
        for (let i = 0; i < 6; i++) {
          const angle = (Math.PI / 3) * i - Math.PI / 2;
          points.push(`${x + size * Math.cos(angle)},${y + size * Math.sin(angle)}`);
        }
        svgContent += `<polygon points="${points.join(' ')}" fill="${color}" stroke="white" stroke-width="2"/>`;
        svgContent += `<text x="${x}" y="${y}" fill="white" text-anchor="middle" dominant-baseline="middle" font-size="10" font-weight="bold">${node.is_confirmed_cc ? '⚡' : '?'}</text>`;
      } else {
        // Circle for regular nodes
        svgContent += `<circle cx="${x}" cy="${y}" r="${size}" fill="${color}" stroke="rgba(255,255,255,0.6)" stroke-width="1.5"/>`;
      }

      // Label
      svgContent += `<text x="${x}" y="${y + size + 12}" fill="white" text-anchor="middle" font-size="9" font-family="monospace">${node.id}</text>`;
    });

    svgContent += '</svg>';

    // Download
    const blob = new Blob([svgContent], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = `network-topology-${new Date().toISOString().split('T')[0]}.svg`;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  }, [graphData, dimensions]);

  const handleNodeClick = (node: any) => {
    setSelectedNode(node as DiscoveryGraphNode);
    // Don't auto-zoom aggressively on every click, just center gently
    fgRef.current?.centerAt(node.x as number, node.y as number, 500);
    fgRef.current?.zoom(3, 500);
  };

  const handleBackgroundClick = () => {
    setSelectedNode(null);
    setShowDetailModal(false);
  };

  const handleCloseModal = () => {
    setShowDetailModal(false);
  };

  // Helper to find the actual data object for the modal
  const getDetailItem = (
    node: DiscoveryGraphNode
  ): {
    item: BotnetCluster | HubNode | DiscoveryGraphNode | null;
    category: 'botnet' | 'hub' | 'attacker' | null;
  } => {
    if (!node) return { item: null, category: null };

    if (node.is_hub) {
      const hub = result.hub_nodes.find((h) => h.ip === node.id);
      return { item: hub || null, category: 'hub' };
    } else if (node.cluster_id !== null) {
      const botnet = result.botnets.find((b) => b.cluster_id === String(node.cluster_id));
      return { item: botnet || null, category: 'botnet' };
    }
    return { item: node, category: 'attacker' };
  };

  const { item: detailItem, category: detailCategory } = selectedNode
    ? getDetailItem(selectedNode)
    : { item: null, category: null };

  // Handle node hover
  const handleNodeHover = useCallback((node: any) => {
    setHoveredNode(node as DiscoveryGraphNode | null);
    if (containerRef.current) {
      containerRef.current.style.cursor = node ? 'pointer' : 'grab';
    }
  }, []);

  // Determine node color based on community or type
  const getCommunityColor = (node: any) => {
    if (node.is_hub) return node.is_confirmed_cc ? '#ff4757' : '#ffaa00';

    // Use community_id for coloring if available
    if (node.community_id !== undefined) {
      const colors = [
        '#2ed573',
        '#1e90ff',
        '#a55eea',
        '#ffa502',
        '#00d2d3',
        '#ff6b81',
        '#7bed9f',
        '#70a1ff',
      ];
      return colors[node.community_id % colors.length];
    }
    return getNodeColor(node);
  };

  // Clean, minimal node rendering
  const paintNode = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const size = getNodeSize(node);
      const color = getCommunityColor(node);
      const x = node.x || 0;
      const y = node.y || 0;
      const isSelected = selectedNode?.id === node.id;
      const isHovered = hoveredNode?.id === node.id;

      // Hub nodes: Hexagon shape
      if (node.is_hub) {
        // Main hexagon
        drawHexagon(ctx, x, y, size);

        // Fill with color
        ctx.fillStyle = color;
        ctx.fill();

        // Border: solid for confirmed, dashed for potential
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        if (!node.is_confirmed_cc) {
          ctx.setLineDash([3, 2]);
        }
        ctx.stroke();
        ctx.setLineDash([]);

        // Icon: ⚡ for confirmed, ? for potential
        ctx.fillStyle = '#ffffff';
        ctx.font = `bold ${Math.max(10, size * 0.5)}px Arial`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(node.is_confirmed_cc ? '⚡' : '?', x, y);
      } else {
        // Regular nodes: Circle
        ctx.beginPath();
        ctx.arc(x, y, size, 0, 2 * Math.PI);
        ctx.fillStyle = color;
        ctx.fill();

        // Border based on Threat Score
        if (node.threat_score && node.threat_score > 0.7) {
          ctx.strokeStyle = '#ff4757'; // High threat red border
          ctx.lineWidth = 2;
        } else {
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
          ctx.lineWidth = 1.5;
        }
        ctx.stroke();
      }

      // Selection ring
      if (isSelected || isHovered) {
        ctx.beginPath();
        ctx.arc(x, y, size + 4, 0, 2 * Math.PI);
        ctx.strokeStyle = isSelected ? '#00ffff' : '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Labels - show for hubs always, others on hover/zoom
      if (node.is_hub || isHovered || isSelected || globalScale > 2) {
        const label = node.id;
        let subLabel = '';
        if (node.ja4_fingerprint) subLabel = `JA4: ${node.ja4_fingerprint.substring(0, 8)}...`;

        const fontSize = 10;
        ctx.font = `600 ${fontSize}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';

        const textWidth = ctx.measureText(label).width;
        const padX = 4;
        const padY = 3;
        const labelY = y + size + 5;

        // Background
        ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
        ctx.beginPath();
        ctx.roundRect(
          x - textWidth / 2 - padX,
          labelY - padY,
          textWidth + padX * 2,
          (subLabel ? fontSize * 2 : fontSize) + padY * 2,
          3
        );
        ctx.fill();

        // Text
        ctx.fillStyle = '#ffffff';
        ctx.fillText(label, x, labelY);

        if (subLabel) {
          ctx.fillStyle = '#aaa';
          ctx.font = `400 ${fontSize - 1}px Inter, sans-serif`;
          ctx.fillText(subLabel, x, labelY + fontSize + 2);
        }
      }
    },
    [selectedNode, hoveredNode]
  );

  // Simple link rendering
  const paintLink = useCallback((link: any, ctx: CanvasRenderingContext2D) => {
    const start = link.source;
    const end = link.target;

    if (!start.x || !start.y || !end.x || !end.y) return;

    const isIntraCluster = link.is_intra_cluster;
    const color = isIntraCluster ? getNodeColor(start) : '#ffffff';
    const opacity = isIntraCluster ? 0.4 : 0.15;
    const lineWidth = isIntraCluster ? 1.5 : 1;

    ctx.beginPath();
    ctx.moveTo(start.x, start.y);
    ctx.lineTo(end.x, end.y);
    ctx.strokeStyle = isIntraCluster ? `${color}66` : `rgba(255, 255, 255, ${opacity})`;
    ctx.lineWidth = lineWidth;
    ctx.stroke();
  }, []);

  // Unique clusters for legend
  const uniqueClusters = useMemo(() => {
    if (!result.graph_data?.clusters) return [];
    // Filter out duplicates and undefined/null ids
    return result.graph_data.clusters
      .filter(
        (c, index, self) =>
          c.id &&
          c.id !== 'undefined' &&
          c.id !== 'null' &&
          index === self.findIndex((t) => t.id === c.id)
      )
      .slice(0, 8);
  }, [result]);

  // Determine which node to display details for (Hover takes precedence for quick preview, Selection locks it)
  // If a node is selected, we show that node's details UNLESS the user hovers another one.
  // Actually, usually "Selection" "locks" the view. Let's make Selection stick.
  // If Selected -> Show Selected.
  // If Not Selected -> Show Hovered.
  const displayedNode = selectedNode || hoveredNode;

  return (
    <div
      className={`discovery-graph-wrapper ${isFullscreen ? 'fullscreen' : ''}`}
      ref={containerRef}
    >
      {/* Grid background overlay */}
      <div className="graph-grid-overlay" />

      {graphData.nodes.length === 0 ? (
        <div className="empty-graph-message">
          <div className="empty-icon">🕸️</div>
          <div className="empty-title">No Graph Data Available</div>
          <div className="empty-subtitle">Run an analysis to discover network relationships</div>
        </div>
      ) : (
        <ForceGraph2D
          ref={fgRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={graphData}
          nodeLabel={() => ''}
          nodeCanvasObject={paintNode}
          nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
            const size = getNodeSize(node);
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(node.x || 0, node.y || 0, size + 8, 0, 2 * Math.PI);
            ctx.fill();
          }}
          linkCanvasObject={paintLink}
          linkDirectionalParticles={0}
          onNodeClick={handleNodeClick}
          onNodeHover={handleNodeHover}
          onBackgroundClick={handleBackgroundClick}
          enableNodeDrag={true}
          enableZoomInteraction={true}
          enablePanInteraction={true}
          cooldownTicks={200}
          cooldownTime={3000}
          d3AlphaDecay={0.015}
          d3VelocityDecay={0.35}
          d3AlphaMin={0.001}
          backgroundColor="transparent"
          onEngineStop={() => {
            if (!isInitialized) {
              fgRef.current?.zoomToFit(400, 80);
              setIsInitialized(true);
            }
          }}
        />
      )}

      {/* Graph Controls Toolbar */}
      <GraphControls
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onFitView={handleFitView}
        onRecenter={handleRecenter}
        onFocusHubs={handleFocusHubs}
        hasHubs={result.hub_nodes.length > 0}
        onExportPNG={handleExportPNG}
        onExportSVG={handleExportSVG}
        hasConfirmedCC={result.hub_nodes.some((h: any) => h.is_confirmed_cc)}
        onToggleFullscreen={handleToggleFullscreen}
        isFullscreen={isFullscreen}
      />

      {/* Stats Overlay */}
      <GraphStats
        nodeCount={result.graph_data?.nodes.length || 0}
        edgeCount={result.graph_data?.edges.length || 0}
        clusterCount={result.graph_data?.clusters.length || 0}
      />

      {/* Enhanced Legend */}
      <GraphLegend clusters={uniqueClusters} />

      {/* Hover/Selection Tooltip (Details Panel) */}
      {displayedNode && (
        <NodeTooltip
          node={displayedNode}
          isLocked={!!selectedNode}
          onViewDetails={() => setShowDetailModal(true)}
        />
      )}

      {showDetailModal && selectedNode && detailItem && detailCategory && (
        <DiscoveryDetailModal
          item={detailItem}
          category={detailCategory}
          onClose={handleCloseModal}
        />
      )}
    </div>
  );
}
