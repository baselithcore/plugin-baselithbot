import { useRef, useMemo, useEffect, useState, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import type { ForceGraphMethods } from 'react-force-graph-2d';
import * as d3 from 'd3';
import { DiscoveryDetailModal } from '../DiscoveryDetailModal';
import { GraphControls } from '../GraphControls';
import { GraphStats } from '../GraphStats';
import { GraphLegend } from '../GraphLegend';
import { NodeTooltip } from '../NodeTooltip';
import { getNodeSize } from '../../utils/graphHelpers';
import { useGraphControls } from './hooks';
import { paintNode, paintLink } from './painters';
import type { DiscoveryGraphProps } from './types';
import './DiscoveryGraph.css';

export function DiscoveryGraph({ result }: DiscoveryGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<ForceGraphMethods>();
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

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

  const controls = useGraphControls(fgRef, containerRef, graphData, dimensions, result);

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
    if (dimensions.width > 0 && !controls.isInitialized) {
      const timer = setTimeout(() => {
        fgRef.current?.zoomToFit(400, 80);
        controls.setIsInitialized(true);
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [dimensions, controls.isInitialized]);

  // Wrap painters with current selected/hovered state
  const paintNodeBound = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      paintNode(node, ctx, globalScale, controls.selectedNode, controls.hoveredNode);
    },
    [controls.selectedNode, controls.hoveredNode]
  );

  const paintLinkBound = useCallback((link: any, ctx: CanvasRenderingContext2D) => {
    paintLink(link, ctx);
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

  return (
    <div
      className={`discovery-graph-wrapper ${controls.isFullscreen ? 'fullscreen' : ''}`}
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
          nodeCanvasObject={paintNodeBound}
          nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
            const size = getNodeSize(node);
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(node.x || 0, node.y || 0, size + 8, 0, 2 * Math.PI);
            ctx.fill();
          }}
          linkCanvasObject={paintLinkBound}
          linkDirectionalParticles={0}
          onNodeClick={controls.handleNodeClick}
          onNodeHover={controls.handleNodeHover}
          onBackgroundClick={controls.handleBackgroundClick}
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
            if (!controls.isInitialized) {
              fgRef.current?.zoomToFit(400, 80);
              controls.setIsInitialized(true);
            }
          }}
        />
      )}

      {/* Graph Controls Toolbar */}
      <GraphControls
        onZoomIn={controls.handleZoomIn}
        onZoomOut={controls.handleZoomOut}
        onFitView={controls.handleFitView}
        onRecenter={controls.handleRecenter}
        onFocusHubs={controls.handleFocusHubs}
        hasHubs={result.hub_nodes.length > 0}
        onExportPNG={controls.handleExportPNG}
        onExportSVG={controls.handleExportSVG}
        hasConfirmedCC={result.hub_nodes.some((h: any) => h.is_confirmed_cc)}
        onToggleFullscreen={controls.handleToggleFullscreen}
        isFullscreen={controls.isFullscreen}
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
      {controls.displayedNode && (
        <NodeTooltip
          node={controls.displayedNode}
          isLocked={!!controls.selectedNode}
          onViewDetails={() => controls.setShowDetailModal(true)}
        />
      )}

      {controls.showDetailModal &&
        controls.selectedNode &&
        controls.detailItem &&
        controls.detailCategory && (
          <DiscoveryDetailModal
            item={controls.detailItem}
            category={controls.detailCategory}
            onClose={controls.handleCloseModal}
          />
        )}
    </div>
  );
}
