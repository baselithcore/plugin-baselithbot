import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import ForceGraph3D, { type ForceGraphMethods } from 'react-force-graph-3d';
import SpriteText from 'three-spritetext';
import type { Object3D } from 'three';
import { motion, AnimatePresence } from 'framer-motion';
import { FileJson, Maximize2, Minimize2, X } from 'lucide-react';
import { toast } from 'sonner';
import type { ExecuteQueryResponse } from '@dbview/shared';
import { colorForKey } from './palette.js';
import { useHoverGuard } from './hover-guard.js';
import { HoverToggle } from './HoverToggle.js';
import { useResizableDrawer } from '../lib/use-resizable-drawer.js';
import { ResizeHandle } from '../components/detail-drawer/DrawerShell.js';

// 3D raycasting + per-frame material updates make hover thrash expensive on
// dense graphs. Above this count, 'auto' mode disables the highlight so camera
// orbit/zoom stay smooth; user can still force-enable via the toolbar.
const HOVER_AUTO_DISABLE_NODES_3D = 600;

interface ResNode {
  id: string;
  label: string;
  group: string;
  color: string;
  val: number;
  degree: number;
  raw: NodeShape;
}

interface ResLink {
  source: string;
  target: string;
  type: string;
  color: string;
}

interface Props {
  result: ExecuteQueryResponse;
}

interface NodeShape {
  _kind: 'node';
  _labels: string[];
  [k: string]: unknown;
}

interface RelShape {
  _kind: 'relationship';
  _type: string;
  [k: string]: unknown;
}

function isNode(v: unknown): v is NodeShape {
  return !!v && typeof v === 'object' && (v as { _kind?: unknown })._kind === 'node';
}

function isRel(v: unknown): v is RelShape {
  return !!v && typeof v === 'object' && (v as { _kind?: unknown })._kind === 'relationship';
}

function nodeId(n: NodeShape): string {
  const id = n.id ?? n._id ?? n.uid;
  if (id !== undefined) return `${n._labels[0] ?? 'Node'}:${String(id)}`;
  return `${n._labels[0] ?? 'Node'}:${JSON.stringify(n).slice(0, 32)}`;
}

function nodeDisplay(n: NodeShape): string {
  const label = n._labels[0] ?? 'Node';
  const name =
    typeof n.name === 'string'
      ? n.name
      : typeof n.title === 'string'
        ? n.title
        : typeof n.id !== 'undefined'
          ? String(n.id)
          : '';
  return name ? `${label}:${name}` : label;
}

export function ResultGraph3DView({ result }: Props) {
  const fgRef = useRef<ForceGraphMethods<ResNode, ResLink> | undefined>(undefined);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [selected, setSelected] = useState<ResNode | null>(null);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const measure = () => setSize({ w: el.clientWidth, h: el.clientHeight });
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const data = useMemo(() => {
    const nodes = new Map<string, ResNode>();
    const links: ResLink[] = [];
    const nodesByOriginalId = new Map<string | number, string>();
    const degree = new Map<string, number>();

    for (const row of result.rows) {
      for (const v of row) {
        if (isNode(v)) {
          const id = nodeId(v);
          if (!nodes.has(id)) {
            const label = v._labels[0] ?? 'Node';
            nodes.set(id, {
              id,
              label: nodeDisplay(v),
              group: label,
              color: colorForKey(label),
              val: 1,
              degree: 0,
              raw: v,
            });
            const origId = v.id ?? v._id ?? v.uid;
            if (
              origId !== undefined &&
              (typeof origId === 'string' || typeof origId === 'number')
            ) {
              nodesByOriginalId.set(origId, id);
            }
          }
        }
      }
    }

    for (const row of result.rows) {
      const rowNodes: string[] = [];
      for (const v of row) if (isNode(v)) rowNodes.push(nodeId(v));
      for (const v of row) {
        if (!isRel(v)) continue;
        const rel = v;
        const srcOrig = (rel as { sourceId?: unknown }).sourceId;
        const tgtOrig = (rel as { targetId?: unknown }).targetId;
        let source: string | undefined;
        let target: string | undefined;
        if (typeof srcOrig === 'string' || typeof srcOrig === 'number') {
          source = nodesByOriginalId.get(srcOrig);
        }
        if (typeof tgtOrig === 'string' || typeof tgtOrig === 'number') {
          target = nodesByOriginalId.get(tgtOrig);
        }
        if ((!source || !target) && rowNodes.length >= 2) {
          source = source ?? rowNodes[0];
          target = target ?? rowNodes[rowNodes.length - 1];
        }
        if (!source || !target) continue;
        links.push({
          source,
          target,
          type: rel._type,
          color: colorForKey(rel._type),
        });
        degree.set(source, (degree.get(source) ?? 0) + 1);
        degree.set(target, (degree.get(target) ?? 0) + 1);
      }
    }

    for (const n of nodes.values()) {
      const d = degree.get(n.id) ?? 0;
      n.degree = d;
      n.val = 4 + Math.sqrt(d) * 3;
    }

    return { nodes: [...nodes.values()], links };
  }, [result]);

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
    autoDisableAbove: HOVER_AUTO_DISABLE_NODES_3D,
  });

  // Spread the cluster: deferred force tuning after the graph is mounted.
  // Numeric arguments only — function arguments to d3Force can crash the
  // simulation when a link's source/target is still a string ID at first tick.
  useEffect(() => {
    if (nodeCount === 0) return;
    const t = setTimeout(() => {
      const fg = fgRef.current;
      if (!fg) return;
      try {
        const charge = fg.d3Force('charge') as
          | { strength?: (n: number) => unknown; distanceMax?: (n: number) => unknown }
          | undefined;
        charge?.strength?.(-200 - Math.min(300, nodeCount * 4));
        charge?.distanceMax?.(700);
        const link = fg.d3Force('link') as { distance?: (n: number) => unknown } | undefined;
        link?.distance?.(90);
        (fg as { d3ReheatSimulation?: () => void }).d3ReheatSimulation?.();
      } catch {
        // Silent: physics tuning is best-effort.
      }
    }, 80);
    return () => clearTimeout(t);
  }, [nodeCount]);

  // Top decile of degrees gets a permanent label sprite. Others rely on the
  // native HTML tooltip (`nodeLabel`) shown on hover.
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

  const hubThreshold = useMemo(() => {
    if (data.nodes.length === 0) return Infinity;
    const sorted = data.nodes.map((n) => n.degree).sort((a, b) => b - a);
    const idx = Math.floor(sorted.length * 0.1);
    return sorted[idx] ?? 0;
  }, [data.nodes]);

  return (
    <div ref={wrapRef} style={{ position: 'absolute', inset: 0 }}>
      {size.w > 0 && size.h > 0 && (
        <ForceGraph3D<ResNode, ResLink>
          ref={fgRef}
          graphData={data}
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
            if (!hoverId) return n.color;
            if (n.id === hoverId) return n.color;
            return neighborsById.get(hoverId)?.has(n.id) ? n.color : '#3a3f4a';
          }}
          nodeLabel={(n) => `${n.label} · ${n.degree} rel`}
          nodeThreeObjectExtend
          nodeThreeObject={(n) => {
            if (n.degree < hubThreshold) return null as unknown as Object3D;
            const sprite = new SpriteText(n.label);
            sprite.color = '#cbd5e1';
            sprite.textHeight = 3.2;
            sprite.fontWeight = '600';
            sprite.fontFace = 'system-ui, sans-serif';
            sprite.padding = 2;
            sprite.borderRadius = 2;
            sprite.backgroundColor = 'rgba(15, 23, 42, 0.55)';
            sprite.position.set(0, 6 * Math.cbrt(n.val) + 4, 0);
            return sprite;
          }}
          linkColor={(l) => {
            if (!hoverId) return l.color;
            const src = typeof l.source === 'object' ? (l.source as ResNode).id : l.source;
            const tgt = typeof l.target === 'object' ? (l.target as ResNode).id : l.target;
            return src === hoverId || tgt === hoverId ? l.color : '#2a2f3a';
          }}
          linkOpacity={hoverId ? 0.85 : 0.5}
          linkWidth={(l) => {
            if (!hoverId) return 1.0;
            const src = typeof l.source === 'object' ? (l.source as ResNode).id : l.source;
            const tgt = typeof l.target === 'object' ? (l.target as ResNode).id : l.target;
            return src === hoverId || tgt === hoverId ? 2.4 : 0.4;
          }}
          linkDirectionalArrowLength={3.5}
          linkDirectionalArrowRelPos={0.92}
          linkDirectionalParticles={(l) => {
            if (!hoverId) return 0;
            const src = typeof l.source === 'object' ? (l.source as ResNode).id : l.source;
            const tgt = typeof l.target === 'object' ? (l.target as ResNode).id : l.target;
            return src === hoverId || tgt === hoverId ? 2 : 0;
          }}
          linkDirectionalParticleSpeed={0.006}
          linkDirectionalParticleWidth={2.5}
          onNodeHover={onNodeHover}
          onEngineStop={() => {
            fgRef.current?.zoomToFit(500, 50);
          }}
          onNodeClick={(node) => {
            const fg = fgRef.current;
            if (fg) {
              const distance = 130;
              const distRatio = 1 + distance / Math.hypot(node.x ?? 1, node.y ?? 1, node.z ?? 1);
              fg.cameraPosition(
                {
                  x: (node.x ?? 0) * distRatio,
                  y: (node.y ?? 0) * distRatio,
                  z: (node.z ?? 0) * distRatio,
                },
                { x: node.x ?? 0, y: node.y ?? 0, z: node.z ?? 0 },
                800,
              );
            }
            setSelected(node);
          }}
        />
      )}
      <Legend nodes={nodeCount} edges={linkCount} />
      <HoverToggle mode={hoverMode} enabled={hoverEnabled} onChange={setHoverMode} />
      <NodeDetailDrawer node={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

interface NodeDetailDrawerProps {
  node: ResNode | null;
  onClose: () => void;
}

function NodeDetailDrawer({ node, onClose }: NodeDetailDrawerProps) {
  const open = !!node;
  const { width, isResizing, isExpanded, toggleExpanded, handleProps } = useResizableDrawer({
    storageKey: 'dbview.node-drawer.width',
  });
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);
  if (typeof document === 'undefined') return null;
  const raw = node?.raw;
  const labels = raw?._labels ?? [];
  const entries = raw ? extractProperties(raw) : [];
  return createPortal(
    <>
      {open && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[2px] animate-fade-in"
          aria-hidden
        />
      )}
      <AnimatePresence>
        {open && raw && (
          <motion.aside
            key="node-detail-drawer"
            role="dialog"
            aria-modal="false"
            aria-label="Node detail"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={isResizing ? { duration: 0 } : { duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            className="fixed top-0 right-0 z-50 h-full max-w-[95vw] flex flex-col border-l shadow-2xl pointer-events-auto"
            style={{
              width: `${width}px`,
              background:
                'linear-gradient(180deg, rgb(var(--surface-elevated)), rgb(var(--surface-1)))',
              borderColor: 'rgb(var(--border-subtle))',
              contain: 'layout',
            }}
          >
            <ResizeHandle isResizing={isResizing} {...handleProps} />
            <div
              className="flex items-center justify-between gap-3 px-4 h-12 border-b shrink-0"
              style={{ borderColor: 'rgb(var(--border-subtle))' }}
            >
              <div className="flex flex-col min-w-0">
                <div className="text-[13px] font-semibold truncate flex items-center gap-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ background: node!.color }}
                    aria-hidden
                  />
                  <span>{node!.label}</span>
                </div>
                <div className="text-[10px] font-mono text-text-dim truncate">
                  {labels.length > 0 ? labels.map((l) => `:${l}`).join(' ') : 'node'} ·{' '}
                  {entries.length} props
                </div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(JSON.stringify(raw, null, 2));
                    toast.success('Node JSON copied');
                  }}
                  className="btn-icon"
                  title="Copy as JSON"
                >
                  <FileJson className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={toggleExpanded}
                  className="btn-icon"
                  title={isExpanded ? 'Restore width' : 'Expand panel'}
                  aria-label={isExpanded ? 'Restore width' : 'Expand panel'}
                  aria-pressed={isExpanded}
                >
                  {isExpanded ? (
                    <Minimize2 className="w-3.5 h-3.5" />
                  ) : (
                    <Maximize2 className="w-3.5 h-3.5" />
                  )}
                </button>
                <button onClick={onClose} className="btn-icon" aria-label="Close">
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
            <div className="flex-1 min-h-0 overflow-auto p-3 flex flex-col gap-1">
              {entries.length === 0 && (
                <div className="text-[12px] text-text-dim italic px-3 py-2">No properties.</div>
              )}
              {entries.map(([key, value]) => (
                <div
                  key={key}
                  className="flex items-start justify-between gap-3 px-3 py-2 rounded-md text-[12px] font-mono"
                  style={{ background: 'rgb(var(--surface-2) / 0.4)' }}
                >
                  <span className="text-text-muted shrink-0">{key}</span>
                  <span className="text-text text-right break-all whitespace-pre-wrap">
                    {formatValue(value)}
                  </span>
                </div>
              ))}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>,
    document.body,
  );
}

const RESERVED_KEYS = new Set(['_kind', '_labels', '_schema', '_id', '_uuid', '_fromId', '_toId']);

function extractProperties(raw: NodeShape): Array<[string, unknown]> {
  const out: Array<[string, unknown]> = [];
  for (const [k, v] of Object.entries(raw)) {
    if (RESERVED_KEYS.has(k)) continue;
    out.push([k, v]);
  }
  return out;
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'string') return v;
  if (typeof v === 'number' || typeof v === 'boolean') return String(v);
  try {
    return JSON.stringify(v, null, 2);
  } catch {
    return String(v);
  }
}

function Legend({ nodes, edges }: { nodes: number; edges: number }) {
  return (
    <div className="absolute bottom-3 left-3 panel-glass px-3 py-1.5 text-[10px] font-mono text-text-muted flex items-center gap-2 z-10 pointer-events-none">
      <span>{nodes} nodes</span>
      <span className="text-text-dim">·</span>
      <span>{edges} rel</span>
      <span className="text-text-dim">·</span>
      <span className="text-text-dim">hover for label</span>
    </div>
  );
}
