import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import ForceGraph3D, { ForceGraph3DInstance } from '3d-force-graph';
import * as THREE from 'three';
import type { AttackSurfaceResp, CyEdge, CyNode } from '../../lib/api';
import { EDGE_COLOR, NODE_BORDER, SEV_RING } from '../../routes/graph/styles';
import { Icon } from './Icon';

type GraphNode = {
  id: string;
  label: string;
  display: string;
  severity: string | null;
  cvss: number | string | null;
  color: string;
  size: number;
  // back-fill at runtime by force-graph
  x?: number;
  y?: number;
  z?: number;
};

type GraphLink = {
  source: string | GraphNode;
  target: string | GraphNode;
  type: string;
  color: string;
  isCritical: boolean;
};

type FocusInfo = { id: string; label: string; display: string };

const SEV_SIZE: Record<string, number> = {
  critical: 7,
  high: 6,
  medium: 5,
  low: 4,
  info: 3.5,
};

const TYPE_SIZE: Record<string, number> = {
  Target: 7,
  CloudResource: 6,
  Endpoint: 5,
  Service: 5,
  Vulnerability: 5,
  Identity: 4,
  DataStore: 5,
  Scanner: 3.5,
  Scan: 3.5,
  CVE: 3,
  CWE: 3,
};

const LEGEND_TYPES: { label: string; color: string }[] = [
  { label: 'Target', color: NODE_BORDER.Target ?? '#00ffd1' },
  { label: 'Endpoint', color: NODE_BORDER.Endpoint ?? '#4cc9f0' },
  { label: 'Service', color: NODE_BORDER.Service ?? '#2dd4bf' },
  { label: 'Identity', color: NODE_BORDER.Identity ?? '#9b87f5' },
  { label: 'CloudResource', color: NODE_BORDER.CloudResource ?? '#5b8cff' },
  { label: 'DataStore', color: NODE_BORDER.DataStore ?? '#86efac' },
  { label: 'Vulnerability', color: NODE_BORDER.Vulnerability ?? '#ff7a18' },
];

const LEGEND_SEV: { label: string; color: string }[] = [
  { label: 'critical', color: SEV_RING.critical ?? '#ff3860' },
  { label: 'high', color: SEV_RING.high ?? '#ff7a18' },
  { label: 'medium', color: SEV_RING.medium ?? '#ffb000' },
  { label: 'low', color: SEV_RING.low ?? '#2dd4bf' },
];

function colorFor(n: CyNode): string {
  const sev = n.data.severity ?? '';
  return SEV_RING[sev] ?? NODE_BORDER[n.data.label] ?? '#9ca3af';
}

function sizeFor(n: CyNode): number {
  const sev = n.data.severity ?? '';
  if (sev && SEV_SIZE[sev]) return SEV_SIZE[sev]!;
  return TYPE_SIZE[n.data.label] ?? 4;
}

function buildGraphData(data: AttackSurfaceResp): {
  nodes: GraphNode[];
  links: GraphLink[];
} {
  const nodeIds = new Set(data.nodes.map((n) => n.data.id));
  const sevById = new Map(data.nodes.map((n) => [n.data.id, n.data.severity ?? '']));
  const nodes: GraphNode[] = data.nodes.map((n: CyNode) => ({
    id: n.data.id,
    label: n.data.label,
    display: n.data.display || n.data.id,
    severity: n.data.severity ?? null,
    cvss: n.data.cvss ?? null,
    color: colorFor(n),
    size: sizeFor(n),
  }));
  const links: GraphLink[] = data.edges
    .filter((e: CyEdge) => nodeIds.has(e.data.source) && nodeIds.has(e.data.target))
    .map((e) => {
      const sevS = sevById.get(e.data.source) ?? '';
      const sevT = sevById.get(e.data.target) ?? '';
      const isCritical = sevS === 'critical' || sevT === 'critical' || e.data.type === 'LATERAL_TO';
      return {
        source: e.data.source,
        target: e.data.target,
        type: e.data.type,
        color: EDGE_COLOR[e.data.type] ?? '#37445a',
        isCritical,
      };
    });
  return { nodes, links };
}

export function Graph3D({
  data,
  highlightIds,
  onSelect,
  onFocusChange,
}: {
  data: AttackSurfaceResp;
  highlightIds?: Set<string>;
  onSelect?: (id: string | null) => void;
  onFocusChange?: (focus: FocusInfo | null) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const fgRef = useRef<ForceGraph3DInstance | null>(null);
  const [hovered, setHovered] = useState<GraphNode | null>(null);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [showLegend, setShowLegend] = useState(true);

  const graphData = useMemo(() => buildGraphData(data), [data]);
  const denseMode = graphData.nodes.length > 180 || graphData.links.length > 320;

  // Adjacency lookup for hover dimming.
  const adj = useMemo(() => {
    const m = new Map<string, Set<string>>();
    for (const link of graphData.links) {
      const s = typeof link.source === 'string' ? link.source : link.source.id;
      const t = typeof link.target === 'string' ? link.target : link.target.id;
      if (!m.has(s)) m.set(s, new Set());
      if (!m.has(t)) m.set(t, new Set());
      m.get(s)!.add(t);
      m.get(t)!.add(s);
    }
    return m;
  }, [graphData]);

  const hoveredId = hovered?.id ?? null;
  const selectedId = selected?.id ?? null;

  const fitView = useCallback(() => {
    fgRef.current?.zoomToFit(700, 60);
  }, []);

  const resetView = useCallback(() => {
    setSelected(null);
    onSelect?.(null);
    onFocusChange?.(null);
    fgRef.current?.cameraPosition({ x: 0, y: 0, z: 320 }, { x: 0, y: 0, z: 0 }, 700);
  }, [onFocusChange, onSelect]);

  // Init once.
  useEffect(() => {
    if (!containerRef.current) return;
    const fg = new ForceGraph3D(containerRef.current) as ForceGraph3DInstance;
    fg.backgroundColor('#070a0f')
      .showNavInfo(false)
      .nodeOpacity(0.95)
      .nodeResolution(16)
      .linkDirectionalArrowLength(2.6)
      .linkDirectionalArrowRelPos(1)
      .linkCurvature(0.08)
      .cooldownTicks(120)
      .warmupTicks(40)
      .d3VelocityDecay(0.32)
      .onNodeHover((n: unknown) => setHovered((n as GraphNode | null) ?? null))
      .onBackgroundClick(() => {
        setSelected(null);
        onSelect?.(null);
        onFocusChange?.(null);
      });

    fgRef.current = fg;

    const ro = new ResizeObserver(() => {
      if (!containerRef.current) return;
      fg.width(containerRef.current.clientWidth);
      fg.height(containerRef.current.clientHeight);
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      try {
        fg._destructor?.();
      } catch {
        /* noop */
      }
      fgRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Click handler depends on onSelect/onFocusChange refs — re-bind each render.
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    fg.onNodeClick((n: unknown) => {
      const node = n as GraphNode;
      setSelected(node);
      onSelect?.(node.id);
      onFocusChange?.({ id: node.id, label: node.label, display: node.display });
      const nx = node.x ?? 0;
      const ny = node.y ?? 0;
      const nz = node.z ?? 0;
      const dist = 110;
      const dr = 1 + dist / Math.max(1, Math.hypot(nx, ny, nz));
      fg.cameraPosition({ x: nx * dr, y: ny * dr, z: nz * dr }, { x: nx, y: ny, z: nz }, 900);
    });
  }, [onSelect, onFocusChange]);

  // Push graph data + dynamic styling.
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    fg.graphData(graphData);

    fg.nodeResolution(denseMode ? 10 : 16)
      .cooldownTicks(denseMode ? 80 : 120)
      .warmupTicks(denseMode ? 24 : 40)
      .linkDirectionalArrowLength(denseMode ? 1.8 : 2.6);

    fg.nodeColor((n: unknown) => (n as GraphNode).color)
      .nodeVal((n: unknown) => (n as GraphNode).size)
      .nodeLabel((n: unknown) => {
        const node = n as GraphNode;
        const sev = node.severity ? ` · ${node.severity}` : '';
        const cvss = node.cvss != null && node.cvss !== '' ? ` · CVSS ${String(node.cvss)}` : '';
        return tooltipHtml(node, sev, cvss);
      });

    fg.linkColor((l: unknown) => (l as GraphLink).color)
      .linkOpacity(denseMode && !selectedId && !hoveredId ? 0.28 : 0.45)
      .linkWidth((l: unknown) => {
        const link = l as GraphLink;
        const s = typeof link.source === 'string' ? link.source : link.source.id;
        const t = typeof link.target === 'string' ? link.target : link.target.id;
        if (selectedId && (s === selectedId || t === selectedId)) return 1.6;
        if (hoveredId && (s === hoveredId || t === hoveredId)) return 1.3;
        if (denseMode) return link.isCritical ? 0.7 : 0.35;
        return link.isCritical ? 0.9 : 0.55;
      })
      .linkDirectionalArrowColor((l: unknown) => (l as GraphLink).color)
      .linkDirectionalParticles((l: unknown) => {
        const link = l as GraphLink;
        const s = typeof link.source === 'string' ? link.source : link.source.id;
        const t = typeof link.target === 'string' ? link.target : link.target.id;
        if (selectedId && (s === selectedId || t === selectedId)) return denseMode ? 2 : 4;
        if (hoveredId && (s === hoveredId || t === hoveredId)) return denseMode ? 1 : 2;
        if (denseMode) return 0;
        if (link.isCritical) return 2;
        return 0;
      })
      .linkDirectionalParticleSpeed(denseMode ? 0.004 : 0.006)
      .linkDirectionalParticleWidth(denseMode ? 1.1 : 1.5);

    fg.nodeThreeObject((n: unknown) => {
      const node = n as GraphNode;
      const isHi = highlightIds?.has(node.id) ?? false;
      const isSel = selectedId === node.id;
      const isHover = hoveredId === node.id;
      const isNeighbor =
        (hoveredId && adj.get(hoveredId)?.has(node.id)) ||
        (selectedId && adj.get(selectedId)?.has(node.id));
      const dim = (hoveredId || selectedId) && !isSel && !isHover && !isNeighbor;

      const group = new THREE.Group();
      const baseColor = new THREE.Color(node.color);
      if (dim) baseColor.multiplyScalar(0.35);
      const sphere = new THREE.Mesh(
        new THREE.SphereGeometry(node.size, denseMode ? 10 : 16, denseMode ? 10 : 16),
        new THREE.MeshLambertMaterial({
          color: baseColor,
          transparent: true,
          opacity: dim ? 0.5 : 0.95,
        })
      );
      group.add(sphere);

      if (isHi || isSel) {
        const ring = new THREE.Mesh(
          new THREE.TorusGeometry(node.size * 1.55, 0.4, 10, 32),
          new THREE.MeshBasicMaterial({ color: isSel ? 0x33dcff : 0xffb000 })
        );
        ring.rotation.x = Math.PI / 2;
        group.add(ring);
        const ring2 = new THREE.Mesh(
          new THREE.TorusGeometry(node.size * 1.95, 0.18, 10, 32),
          new THREE.MeshBasicMaterial({
            color: isSel ? 0x33dcff : 0xffb000,
            transparent: true,
            opacity: 0.5,
          })
        );
        ring2.rotation.x = Math.PI / 3;
        group.add(ring2);
      } else if (node.severity === 'critical') {
        // Pulse glow for critical nodes.
        const glow = new THREE.Mesh(
          new THREE.SphereGeometry(node.size * 1.4, 16, 16),
          new THREE.MeshBasicMaterial({
            color: 0xff3860,
            transparent: true,
            opacity: 0.18,
          })
        );
        group.add(glow);
      }
      return group;
    });
    fg.nodeThreeObjectExtend(false);
  }, [graphData, highlightIds, hoveredId, selectedId, adj, denseMode]);

  // Auto-fit when graph data changes (after force settles).
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    const t = window.setTimeout(() => fg.zoomToFit(800, 80), 1200);
    return () => window.clearTimeout(t);
  }, [graphData]);

  // Keyboard shortcuts: F=fit, R=reset camera, Esc=clear selection.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      if (e.key === 'f' || e.key === 'F') {
        e.preventDefault();
        fitView();
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        resetView();
      } else if (e.key === 'Escape') {
        if (selectedId) {
          setSelected(null);
          onSelect?.(null);
          onFocusChange?.(null);
        }
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [fitView, resetView, selectedId, onSelect, onFocusChange]);

  return (
    <div className="relative h-full w-full overflow-hidden bg-[#070a0f]">
      <div ref={containerRef} className="h-full w-full" />

      <div className="absolute right-3 top-3 flex items-center gap-1 rounded-md border border-bg-line bg-bg-base/85 p-1 shadow-card backdrop-blur">
        <ToolBtn label="Fit graph" onClick={fitView} icon={<Icon.Maximize size={14} />} />
        <ToolBtn label="Reset camera" onClick={resetView} icon={<Icon.Refresh size={14} />} />
        <ToolBtn
          label={showLegend ? 'Hide legend' : 'Show legend'}
          onClick={() => setShowLegend((v) => !v)}
          icon={<Icon.Help size={14} />}
        />
      </div>

      {/* Legend */}
      {showLegend && <Legend3D />}

      {/* Selected node card */}
      {selected && (
        <div className="absolute bottom-3 left-3 max-w-[min(420px,calc(100%-6rem))] rounded-lg border border-bg-line bg-bg-base/90 px-3 py-2.5 text-xs shadow-elevated backdrop-blur">
          <div className="flex items-center gap-2">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ background: selected.color }}
            />
            <span className="font-mono text-2xs uppercase tracking-wider text-text-muted">
              {selected.label}
              {selected.severity ? ` · ${selected.severity}` : ''}
            </span>
            <button
              type="button"
              onClick={() => {
                setSelected(null);
                onSelect?.(null);
                onFocusChange?.(null);
              }}
              className="ml-auto grid h-6 w-6 place-items-center rounded text-text-muted transition hover:bg-bg-overlay hover:text-text-primary"
              aria-label="Clear selection"
            >
              <Icon.X size={12} />
            </button>
          </div>
          <div className="mt-1 break-all font-mono text-text-primary">{selected.display}</div>
          <div className="mt-1.5 flex items-center gap-3 font-mono text-2xs text-text-muted">
            <span title="degree">deg {adj.get(selected.id)?.size ?? 0}</span>
            {selected.cvss != null && selected.cvss !== '' && (
              <span>cvss {String(selected.cvss)}</span>
            )}
            <span className="opacity-60">{selected.id.slice(0, 24)}</span>
          </div>
        </div>
      )}

      {/* Hover hint */}
      {hovered && !selected && (
        <div className="pointer-events-none absolute bottom-3 left-3 max-w-[min(360px,calc(100%-6rem))] truncate rounded border border-bg-line bg-bg-base/80 px-2 py-1 font-mono text-2xs text-text-muted backdrop-blur">
          {hovered.label} · {hovered.display.slice(0, 50)}
        </div>
      )}

      {/* Status overlay */}
      <div className="pointer-events-none absolute bottom-3 right-3 rounded border border-bg-line bg-bg-base/70 px-2 py-1 font-mono text-2xs text-text-muted backdrop-blur">
        {graphData.nodes.length}n · {graphData.links.length}e
      </div>
    </div>
  );
}

function ToolBtn({
  label,
  onClick,
  icon,
}: {
  label: string;
  onClick: () => void;
  icon: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      aria-label={label}
      className="grid h-8 w-8 place-items-center rounded text-text-muted transition-colors hover:bg-bg-overlay hover:text-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
    >
      {icon}
    </button>
  );
}

function Legend3D() {
  return (
    <div className="absolute left-3 top-3 max-w-[220px] rounded-md border border-bg-line bg-bg-base/85 px-2.5 py-2 text-2xs shadow-card backdrop-blur">
      <p className="mb-1 font-mono uppercase tracking-wider text-text-muted">Types</p>
      <ul className="grid grid-cols-2 gap-x-2 gap-y-1">
        {LEGEND_TYPES.map((t) => (
          <li key={t.label} className="flex items-center gap-1.5 font-mono text-text-secondary">
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: t.color }} />
            <span className="truncate">{t.label}</span>
          </li>
        ))}
      </ul>
      <p className="mb-1 mt-2 font-mono uppercase tracking-wider text-text-muted">Severity</p>
      <ul className="flex flex-wrap gap-x-2 gap-y-1">
        {LEGEND_SEV.map((s) => (
          <li key={s.label} className="flex items-center gap-1 font-mono text-text-secondary">
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: s.color }} />
            <span>{s.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function tooltipHtml(node: GraphNode, sev: string, cvss: string): string {
  const safeDisplay = escapeHtml(node.display);
  const safeLabel = escapeHtml(node.label + sev + cvss);
  return `<div style="font-family:monospace;font-size:11px;padding:4px 6px;background:#0a0e14;border:1px solid #1f2937;border-radius:4px;color:#e7ecf7;max-width:320px"><b>${safeDisplay}</b><br/><span style="opacity:0.7">${safeLabel}</span></div>`;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
