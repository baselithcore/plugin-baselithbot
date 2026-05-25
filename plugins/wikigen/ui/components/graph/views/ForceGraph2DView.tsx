import { useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph2D, { type ForceGraphMethods } from 'react-force-graph-2d';

import type { GraphData, GraphNode } from '../../../lib/api/graph';
import {
  DIMMED_LINK,
  DIMMED_NODE,
  buildFGData,
  edgeBaseColor,
  edgeBaseWidth,
  isLinkVisible,
  isNodeVisible,
  linkEndpointId,
  type FGLink,
  type FGNode,
} from './adapter';
import { useGraphSize } from './useGraphSize';
import { useHoverGuard } from './useHoverGuard';
import { HoverToggle, LabelToggle, Legend, type LabelMode } from './overlays';

const LABEL_MIN_ZOOM = 0.6;
const HOVER_AUTO_DISABLE_NODES_2D = 1000;
const HUB_PERCENTILE = 0.05;

interface Props {
  data: GraphData;
  visibleKinds: Set<string>;
  visibleCommunities: Set<number>;
  confidenceMin: number;
  search: string;
  onSelectNode: (node: GraphNode | null) => void;
  selectedNodeId: string | null;
}

export function ForceGraph2DView({
  data,
  visibleKinds,
  visibleCommunities,
  confidenceMin,
  search,
  onSelectNode,
  selectedNodeId,
}: Props) {
  const fgRef = useRef<ForceGraphMethods<FGNode, FGLink> | undefined>(undefined);
  const { ref: wrapRef, size } = useGraphSize<HTMLDivElement>();
  const [labelMode, setLabelMode] = useState<LabelMode>('hubs');
  // zoomToFit only on FIRST engine stop. Subsequent stops fire on micro-
  // reheats (filter accessor churn) and would yank the user's pan/zoom.
  const hasFitOnceRef = useRef(false);

  // Stable graphData identity — see ForceGraph3DView for full reasoning.
  // Filters are applied via color-dim accessors, not by rebuilding fg.
  const fg = useMemo(
    () => buildFGData(data, { visibleKinds, visibleCommunities, confidenceMin }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [data],
  );

  useEffect(() => {
    hasFitOnceRef.current = false;
  }, [fg]);

  const visibleNodeIds = useMemo(() => {
    const set = new Set<string>();
    for (const n of fg.nodes) if (isNodeVisible(n, { visibleKinds, visibleCommunities, confidenceMin }, search)) set.add(n.id);
    return set;
  }, [fg.nodes, visibleKinds, visibleCommunities, confidenceMin, search]);

  const nodeCount = fg.nodes.length;
  const linkCount = fg.links.length;

  const { hoverId, onNodeHover, enabled: hoverEnabled, mode: hoverMode, setMode: setHoverMode } =
    useHoverGuard<FGNode>({
      containerRef: wrapRef,
      nodeCount,
      autoDisableAbove: HOVER_AUTO_DISABLE_NODES_2D,
    });

  // Tune d3 forces by sqrt(n) once nodes are mounted. Function args only —
  // passing functions to d3Force can crash the sim while link source/target
  // are still string IDs at first tick.
  useEffect(() => {
    if (nodeCount === 0) return;
    const t = window.setTimeout(() => {
      const inst = fgRef.current;
      if (!inst) return;
      try {
        const density = Math.sqrt(nodeCount);
        const charge = inst.d3Force('charge') as
          | { strength?: (n: number) => unknown; distanceMax?: (n: number) => unknown }
          | undefined;
        charge?.strength?.(-(120 + density * 18));
        charge?.distanceMax?.(900);
        const link = inst.d3Force('link') as { distance?: (n: number) => unknown } | undefined;
        link?.distance?.(60 + density * 2);
        (inst as { d3ReheatSimulation?: () => void }).d3ReheatSimulation?.();
      } catch {
        // best-effort
      }
    }, 80);
    return () => window.clearTimeout(t);
  }, [nodeCount]);

  // Hub threshold: top decile by degree. Require ≥1 relation so an
  // edge-less graph doesn't label every node.
  const hubThreshold = useMemo(() => {
    if (fg.nodes.length === 0) return Infinity;
    const sorted = fg.nodes.map((n) => n.degree).sort((a, b) => b - a);
    const idx = Math.floor(sorted.length * HUB_PERCENTILE);
    return Math.max(1, sorted[idx] ?? 1);
  }, [fg.nodes]);

  useEffect(() => {
    if (!selectedNodeId) return;
    const inst = fgRef.current;
    if (!inst) return;
    const node = fg.nodes.find((n) => n.id === selectedNodeId);
    if (!node || typeof node.x !== 'number' || typeof node.y !== 'number') return;
    inst.centerAt(node.x, node.y, 600);
    inst.zoom(2.4, 600);
  }, [selectedNodeId, fg.nodes]);

  return (
    <div ref={wrapRef} className="relative h-full w-full overflow-hidden rounded-2xl border border-[var(--color-border)] bg-canvas-raised">
      {size.w > 0 && size.h > 0 && (
        <ForceGraph2D<FGNode, FGLink>
          ref={fgRef}
          graphData={fg}
          width={size.w}
          height={size.h}
          backgroundColor="rgba(0,0,0,0)"
          cooldownTicks={150}
          nodeRelSize={6}
          nodeVal={(n) => n.val}
          nodeColor={(n) => {
            if (!visibleNodeIds.has(n.id)) return DIMMED_NODE;
            if (!hoverId) return n.color;
            if (n.id === hoverId) return n.color;
            return fg.neighborsById.get(hoverId)?.has(n.id) ? n.color : DIMMED_NODE;
          }}
          nodeLabel={(n) => `${n.name} · ${n.kind} · ${n.degree} rel · C${n.community}`}
          nodeCanvasObjectMode={(n) => {
            if (labelMode === 'off' && n.id !== hoverId) return undefined;
            if (n.id === hoverId) return 'after';
            if (n.id === selectedNodeId) return 'after';
            if (labelMode === 'all') return 'after';
            return n.degree >= hubThreshold ? 'after' : undefined;
          }}
          nodeCanvasObject={(n, ctx, scale) => {
            const isFocus = n.id === hoverId || n.id === selectedNodeId;
            const isHub = n.degree >= hubThreshold;
            if (!isFocus) {
              if (labelMode === 'off') return;
              if (labelMode === 'hubs' && !isHub) return;
              if (labelMode === 'all' && !isHub && scale < LABEL_MIN_ZOOM) return;
            }
            if (!visibleNodeIds.has(n.id) && !isFocus) return;
            const label = n.name;
            const fontSize = (isFocus || isHub ? 12 : 10) / scale;
            ctx.font = `${isFocus || isHub ? 600 : 500} ${fontSize}px system-ui, sans-serif`;
            const tw = ctx.measureText(label).width;
            const px = 4 / scale;
            const py = 2 / scale;
            const r = Math.sqrt(n.val) * 2;
            const x = (n.x ?? 0) - tw / 2 - px;
            const y = (n.y ?? 0) + r + 4 / scale;
            ctx.fillStyle = isFocus ? 'rgba(15, 23, 42, 0.92)' : 'rgba(15, 23, 42, 0.65)';
            ctx.fillRect(x, y, tw + px * 2, fontSize + py * 2);
            ctx.fillStyle = isFocus ? '#f1f5f9' : '#cbd5e1';
            ctx.textBaseline = 'top';
            ctx.fillText(label, x + px, y + py);
          }}
          linkColor={(l) => {
            if (!isLinkVisible(l, visibleNodeIds, confidenceMin)) return DIMMED_LINK;
            if (!hoverId) return edgeBaseColor();
            const src = linkEndpointId(l.source as string | object);
            const tgt = linkEndpointId(l.target as string | object);
            return src === hoverId || tgt === hoverId ? edgeBaseColor() : DIMMED_LINK;
          }}
          linkWidth={(l) => {
            const base = edgeBaseWidth(l.confidence);
            if (!isLinkVisible(l, visibleNodeIds, confidenceMin)) return 0.3;
            if (!hoverId) return base;
            const src = linkEndpointId(l.source as string | object);
            const tgt = linkEndpointId(l.target as string | object);
            return src === hoverId || tgt === hoverId ? base * 1.8 : base * 0.5;
          }}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={0.96}
          linkDirectionalParticles={(l) => {
            if (!hoverId) return 0;
            const src = linkEndpointId(l.source as string | object);
            const tgt = linkEndpointId(l.target as string | object);
            return src === hoverId || tgt === hoverId ? 2 : 0;
          }}
          linkDirectionalParticleSpeed={0.006}
          linkDirectionalParticleWidth={2.2}
          onNodeHover={onNodeHover}
          onEngineStop={() => {
            if (hasFitOnceRef.current) return;
            hasFitOnceRef.current = true;
            fgRef.current?.zoomToFit(500, 50);
          }}
          onNodeClick={(node) => {
            const inst = fgRef.current;
            if (inst && typeof node.x === 'number' && typeof node.y === 'number') {
              inst.centerAt(node.x, node.y, 600);
              inst.zoom(2.4, 600);
            }
            const original = data.nodes.find((n) => n.id === node.id) ?? null;
            onSelectNode(original);
          }}
          onBackgroundClick={() => onSelectNode(null)}
        />
      )}
      <Legend nodes={nodeCount} edges={linkCount} hint={hoverEnabled ? 'hover per vicini' : 'click per dettaglio'} />
      <LabelToggle mode={labelMode} onChange={setLabelMode} />
      <HoverToggle mode={hoverMode} enabled={hoverEnabled} onChange={setHoverMode} bottomPx={56} />
    </div>
  );
}
