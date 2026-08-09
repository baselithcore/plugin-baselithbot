import { useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph2D, { type ForceGraphMethods } from 'react-force-graph-2d';
import type { ExecuteQueryResponse } from '@dbview/shared';
import { buildGraphData } from './result-graph-2d/data.js';
import { Legend, LabelToggle } from './result-graph-2d/overlay.js';
import { NodeDetailDrawer } from './result-graph-2d/NodeDetailDrawer.js';
import type { LabelMode, ResLink, ResNode } from './result-graph-2d/types.js';
import { useHoverGuard } from './hover-guard.js';
import { HoverToggle } from './HoverToggle.js';

const LABEL_MIN_ZOOM = 0.6;
const HOVER_AUTO_DISABLE_NODES_2D = 1000;

interface Props {
  result: ExecuteQueryResponse;
}

export function ResultGraph2DView({ result }: Props) {
  const fgRef = useRef<ForceGraphMethods<ResNode, ResLink> | undefined>(undefined);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [selected, setSelected] = useState<ResNode | null>(null);
  const [labelMode, setLabelMode] = useState<LabelMode>('hubs');

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const measure = () => setSize({ w: el.clientWidth, h: el.clientHeight });
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const data = useMemo(() => buildGraphData(result), [result]);

  const nodeCount = data.nodes.length;
  const linkCount = data.links.length;

  const {
    hoverId,
    onNodeHover,
    enabled: hoverEnabled,
    mode: hoverMode,
    setMode: setHoverMode,
  } = useHoverGuard<ResNode>({
    containerRef: wrapRef,
    nodeCount,
    autoDisableAbove: HOVER_AUTO_DISABLE_NODES_2D,
  });

  useEffect(() => {
    if (nodeCount === 0) return;
    const t = setTimeout(() => {
      const fg = fgRef.current;
      if (!fg) return;
      try {
        // Charge and link distance scale with sqrt(nodeCount) so layout stays
        // legible from a few dozen up to thousands of nodes.
        const density = Math.sqrt(nodeCount);
        const charge = fg.d3Force('charge') as
          { strength?: (n: number) => unknown; distanceMax?: (n: number) => unknown } | undefined;
        charge?.strength?.(-(120 + density * 18));
        charge?.distanceMax?.(900);
        const link = fg.d3Force('link') as { distance?: (n: number) => unknown } | undefined;
        link?.distance?.(60 + density * 2);
        (fg as { d3ReheatSimulation?: () => void }).d3ReheatSimulation?.();
      } catch {
        // Silent: physics tuning is best-effort.
      }
    }, 80);
    return () => clearTimeout(t);
  }, [nodeCount]);

  const neighborsById = useMemo(() => {
    const map = new Map<string, Set<string>>();
    for (const l of data.links) {
      const src = typeof l.source === 'object' ? (l.source as ResNode).id : l.source;
      const tgt = typeof l.target === 'object' ? (l.target as ResNode).id : l.target;
      if (!map.has(src)) map.set(src, new Set());
      if (!map.has(tgt)) map.set(tgt, new Set());
      map.get(src)!.add(tgt);
      map.get(tgt)!.add(src);
    }
    return map;
  }, [data]);

  // Top decile by degree, but require at least one relationship to qualify as
  // a hub — otherwise a graph with zero edges would label every single node.
  const hubThreshold = useMemo(() => {
    if (data.nodes.length === 0) return Infinity;
    const sorted = data.nodes.map((n) => n.degree).sort((a, b) => b - a);
    const idx = Math.floor(sorted.length * 0.05);
    return Math.max(1, sorted[idx] ?? 1);
  }, [data.nodes]);

  return (
    <div ref={wrapRef} style={{ position: 'absolute', inset: 0 }}>
      {size.w > 0 && size.h > 0 && (
        <ForceGraph2D<ResNode, ResLink>
          ref={fgRef}
          graphData={data}
          width={size.w}
          height={size.h}
          backgroundColor="rgba(0,0,0,0)"
          cooldownTicks={150}
          nodeRelSize={6}
          nodeVal={(n) => n.val}
          nodeColor={(n) => {
            if (!hoverId) return n.color;
            if (n.id === hoverId) return n.color;
            return neighborsById.get(hoverId)?.has(n.id) ? n.color : '#3a3f4a';
          }}
          nodeLabel={(n) => `${n.label} · ${n.degree} rel`}
          nodeCanvasObjectMode={(n) => {
            if (labelMode === 'off') return undefined;
            if (n.id === hoverId) return 'after';
            if (labelMode === 'all') return 'after';
            return n.degree >= hubThreshold ? 'after' : undefined;
          }}
          nodeCanvasObject={(n, ctx, scale) => {
            if (labelMode === 'off' && n.id !== hoverId) return;
            const isHub = n.degree >= hubThreshold;
            const isFocus = n.id === hoverId;
            if (!isFocus) {
              if (labelMode === 'hubs' && !isHub) return;
              // Hide non-hub labels until user zooms in — keeps dense graphs
              // readable at fit-view scale, reveals detail on inspection.
              if (labelMode === 'all' && !isHub && scale < LABEL_MIN_ZOOM) return;
            }
            const label = n.label;
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
            if (!hoverId) return l.color;
            const src = typeof l.source === 'object' ? (l.source as ResNode).id : l.source;
            const tgt = typeof l.target === 'object' ? (l.target as ResNode).id : l.target;
            return src === hoverId || tgt === hoverId ? l.color : '#2a2f3a';
          }}
          linkWidth={(l) => {
            if (!hoverId) return 1.0;
            const src = typeof l.source === 'object' ? (l.source as ResNode).id : l.source;
            const tgt = typeof l.target === 'object' ? (l.target as ResNode).id : l.target;
            return src === hoverId || tgt === hoverId ? 2.4 : 0.5;
          }}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={0.96}
          linkDirectionalParticles={(l) => {
            if (!hoverId) return 0;
            const src = typeof l.source === 'object' ? (l.source as ResNode).id : l.source;
            const tgt = typeof l.target === 'object' ? (l.target as ResNode).id : l.target;
            return src === hoverId || tgt === hoverId ? 2 : 0;
          }}
          linkDirectionalParticleSpeed={0.006}
          linkDirectionalParticleWidth={2.2}
          onNodeHover={onNodeHover}
          onEngineStop={() => {
            fgRef.current?.zoomToFit(500, 50);
          }}
          onNodeClick={(node) => {
            const fg = fgRef.current;
            if (fg && typeof node.x === 'number' && typeof node.y === 'number') {
              fg.centerAt(node.x, node.y, 600);
              fg.zoom(2.4, 600);
            }
            setSelected(node);
          }}
        />
      )}
      <Legend nodes={nodeCount} edges={linkCount} />
      <LabelToggle mode={labelMode} onChange={setLabelMode} />
      <HoverToggle mode={hoverMode} enabled={hoverEnabled} onChange={setHoverMode} bottomPx={56} />
      <NodeDetailDrawer node={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
