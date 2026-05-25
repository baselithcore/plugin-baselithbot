import { useEffect, useMemo, useRef } from 'react';
import ForceGraph3D, { type ForceGraphMethods } from 'react-force-graph-3d';
import SpriteText from 'three-spritetext';
import type { Object3D } from 'three';

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
import { HoverToggle, Legend } from './overlays';

// 3D raycasting + per-frame material updates make hover thrash expensive on
// dense graphs. Above this count, 'auto' disables highlight so camera
// orbit/zoom stay smooth; user can force-enable from the toolbar.
const HOVER_AUTO_DISABLE_NODES_3D = 600;
const HUB_PERCENTILE_3D = 0.1;

interface Props {
  data: GraphData;
  visibleKinds: Set<string>;
  visibleCommunities: Set<number>;
  confidenceMin: number;
  search: string;
  onSelectNode: (node: GraphNode | null) => void;
  selectedNodeId: string | null;
}

export function ForceGraph3DView({
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
  // zoomToFit only on FIRST engine stop. Subsequent stops happen on micro-
  // reheats from hover-induced accessor identity churn — refitting then snaps
  // camera back and corrupts orbit/zoom the user just performed.
  const hasFitOnceRef = useRef(false);

  // Stable graphData identity. buildFGData reads only `data` — folding
  // filter state into deps would yield a new fg reference on every slider
  // tick, which react-force-graph treats as a fresh dataset and resets node
  // positions (simulation restart → nodes scatter off-camera). Filters are
  // applied downstream via color-dim accessors, not by rebuilding fg.
  const fg = useMemo(
    () => buildFGData(data, { visibleKinds, visibleCommunities, confidenceMin }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [data],
  );

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
      autoDisableAbove: HOVER_AUTO_DISABLE_NODES_3D,
    });

  // New graphData reference (filter change, reload) = allow one fresh fit.
  useEffect(() => {
    hasFitOnceRef.current = false;
  }, [fg]);

  useEffect(() => {
    if (nodeCount === 0) return;
    const t = window.setTimeout(() => {
      const inst = fgRef.current;
      if (!inst) return;
      try {
        const charge = inst.d3Force('charge') as
          | { strength?: (n: number) => unknown; distanceMax?: (n: number) => unknown }
          | undefined;
        charge?.strength?.(-200 - Math.min(300, nodeCount * 4));
        charge?.distanceMax?.(700);
        const link = inst.d3Force('link') as { distance?: (n: number) => unknown } | undefined;
        link?.distance?.(90);
        (inst as { d3ReheatSimulation?: () => void }).d3ReheatSimulation?.();
      } catch {
        // best-effort
      }
    }, 80);
    return () => window.clearTimeout(t);
  }, [nodeCount]);

  const hubThreshold = useMemo(() => {
    if (fg.nodes.length === 0) return Infinity;
    const sorted = fg.nodes.map((n) => n.degree).sort((a, b) => b - a);
    const idx = Math.floor(sorted.length * HUB_PERCENTILE_3D);
    return Math.max(1, sorted[idx] ?? 1);
  }, [fg.nodes]);

  useEffect(() => {
    if (!selectedNodeId) return;
    const inst = fgRef.current;
    if (!inst) return;
    const node = fg.nodes.find((n) => n.id === selectedNodeId);
    if (!node) return;
    const distance = 130;
    const x = node.x ?? 0;
    const y = node.y ?? 0;
    const z = node.z ?? 0;
    const distRatio = 1 + distance / Math.max(1, Math.hypot(x, y, z));
    inst.cameraPosition(
      { x: x * distRatio, y: y * distRatio, z: z * distRatio },
      { x, y, z },
      800,
    );
  }, [selectedNodeId, fg.nodes]);

  return (
    <div ref={wrapRef} className="relative h-full w-full overflow-hidden rounded-2xl border border-[var(--color-border)] bg-canvas-raised">
      {size.w > 0 && size.h > 0 && (
        <ForceGraph3D<FGNode, FGLink>
          ref={fgRef}
          graphData={fg}
          width={size.w}
          height={size.h}
          backgroundColor="rgba(0,0,0,0)"
          showNavInfo={false}
          enableNodeDrag
          cooldownTicks={150}
          nodeRelSize={6}
          nodeOpacity={0.92}
          nodeResolution={20}
          nodeVal={(n) => n.val}
          nodeColor={(n) => {
            if (!visibleNodeIds.has(n.id)) return DIMMED_NODE;
            if (!hoverId) return n.color;
            if (n.id === hoverId) return n.color;
            return fg.neighborsById.get(hoverId)?.has(n.id) ? n.color : DIMMED_NODE;
          }}
          nodeLabel={(n) => `${n.name} · ${n.kind} · ${n.degree} rel · C${n.community}`}
          nodeThreeObjectExtend
          nodeThreeObject={(n) => {
            // IMPORTANT: accessor must NOT depend on hover state. Rebuilding
            // sprites on hover triggers engine.refresh → micro-reheat →
            // onEngineStop re-fires → camera fit yanks the view. Hovered nodes
            // get the native HTML tooltip via `nodeLabel` instead.
            const isSelected = n.id === selectedNodeId;
            if (!isSelected && n.degree < hubThreshold) return null as unknown as Object3D;
            const sprite = new SpriteText(n.name);
            sprite.color = isSelected ? '#f1f5f9' : '#cbd5e1';
            sprite.textHeight = isSelected ? 4 : 3.2;
            sprite.fontWeight = '600';
            sprite.fontFace = 'system-ui, sans-serif';
            sprite.padding = 2;
            sprite.borderRadius = 2;
            sprite.backgroundColor = isSelected ? 'rgba(15,23,42,0.92)' : 'rgba(15,23,42,0.55)';
            sprite.position.set(0, 6 * Math.cbrt(n.val) + 4, 0);
            return sprite;
          }}
          linkColor={(l) => {
            if (!isLinkVisible(l, visibleNodeIds, confidenceMin)) return DIMMED_LINK;
            if (!hoverId) return edgeBaseColor();
            const src = linkEndpointId(l.source as string | object);
            const tgt = linkEndpointId(l.target as string | object);
            return src === hoverId || tgt === hoverId ? edgeBaseColor() : DIMMED_LINK;
          }}
          linkOpacity={hoverId ? 0.85 : 0.5}
          linkWidth={(l) => {
            const base = edgeBaseWidth(l.confidence);
            if (!isLinkVisible(l, visibleNodeIds, confidenceMin)) return 0.2;
            if (!hoverId) return base;
            const src = linkEndpointId(l.source as string | object);
            const tgt = linkEndpointId(l.target as string | object);
            return src === hoverId || tgt === hoverId ? base * 1.8 : base * 0.4;
          }}
          linkDirectionalArrowLength={3.5}
          linkDirectionalArrowRelPos={0.92}
          linkDirectionalParticles={(l) => {
            if (!hoverId) return 0;
            const src = linkEndpointId(l.source as string | object);
            const tgt = linkEndpointId(l.target as string | object);
            return src === hoverId || tgt === hoverId ? 2 : 0;
          }}
          linkDirectionalParticleSpeed={0.006}
          linkDirectionalParticleWidth={2.5}
          onNodeHover={onNodeHover}
          onEngineStop={() => {
            if (hasFitOnceRef.current) return;
            hasFitOnceRef.current = true;
            fgRef.current?.zoomToFit(500, 50);
          }}
          onNodeClick={(node) => {
            const inst = fgRef.current;
            if (inst) {
              const x = node.x ?? 0;
              const y = node.y ?? 0;
              const z = node.z ?? 0;
              const distance = 130;
              const distRatio = 1 + distance / Math.max(1, Math.hypot(x, y, z));
              inst.cameraPosition(
                { x: x * distRatio, y: y * distRatio, z: z * distRatio },
                { x, y, z },
                800,
              );
            }
            const original = data.nodes.find((n) => n.id === node.id) ?? null;
            onSelectNode(original);
          }}
          onBackgroundClick={() => onSelectNode(null)}
        />
      )}
      <Legend nodes={nodeCount} edges={linkCount} hint={hoverEnabled ? 'hover per vicini' : 'orbita libera'} />
      <HoverToggle mode={hoverMode} enabled={hoverEnabled} onChange={setHoverMode} bottomPx={12} />
    </div>
  );
}
