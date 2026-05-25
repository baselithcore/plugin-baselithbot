import { useEffect, useMemo, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import type { Core, Css, ElementDefinition, StylesheetStyle } from 'cytoscape';
// @ts-expect-error — cytoscape-dagre ships no types.
import dagre from 'cytoscape-dagre';
import type { AttackSurfaceResp, CyEdge, CyNode } from '../../lib/api';
import {
  EDGE_COLOR,
  NODE_BORDER,
  NODE_FILL,
  NODE_SHAPE,
  SEV_RING,
} from '../../routes/graph/styles';

let _registered = false;
function ensureExtensionRegistered(): void {
  if (_registered) return;
  cytoscape.use(dagre);
  _registered = true;
}

const TYPE_HINT: Record<string, string> = {
  Target: 'Target',
  Endpoint: 'Endpoint',
  Service: 'Service',
  Vulnerability: 'Finding',
  CVE: 'CVE',
  CWE: 'CWE',
  Scan: 'Scan',
  Scanner: 'Scanner',
  Identity: 'Identity',
  CloudResource: 'Cloud Resource',
  DataStore: 'Data Store',
};

type ClusterMembers = {
  id: string;
  display: string;
  severity?: string | null;
  cvss?: string | number | null;
};

type SelectedNode = {
  id: string;
  label: string;
  type: string;
  display: string;
  severity?: string;
  cvss?: string | number;
  isCluster: boolean;
  members?: ClusterMembers[];
  ring: string;
};

const STYLE: StylesheetStyle[] = [
  {
    selector: 'node',
    style: {
      shape: 'data(shape)' as never,
      'background-color': 'data(fill)',
      'background-opacity': 0.92,
      'border-color': 'data(ring)',
      'border-width': 2.5,
      'border-opacity': 0.96,
      width: 56,
      height: 56,
      label: 'data(display)',
      color: '#e7ecf7',
      'font-family': '"JetBrains Mono Variable", ui-monospace, monospace',
      'font-size': 11,
      'font-weight': 500,
      'text-valign': 'bottom',
      'text-halign': 'center',
      'text-margin-y': 8,
      'text-wrap': 'wrap',
      'text-max-width': '200',
      'line-height': 1.3,
      'text-outline-color': '#0a0e14',
      'text-outline-width': 2.5,
      'text-outline-opacity': 1,
      'overlay-padding': 4,
    } as Css.Node,
  },
  {
    selector: 'node[label = "Target"]',
    style: { width: 70, height: 70, 'font-weight': 700 } as Css.Node,
  },
  {
    selector: 'node[label = "Vulnerability"]',
    style: { width: 64, height: 64, 'border-width': 3.5 } as Css.Node,
  },
  {
    selector: 'node[isCluster = "1"]',
    style: {
      'background-color': '#1a2233',
      'border-style': 'dashed',
      'border-width': 2,
      width: 60,
      height: 60,
    } as Css.Node,
  },
  {
    selector: 'node[severity = "critical"]',
    style: {
      'border-color': '#ff3860',
      'overlay-color': '#ff3860',
      'overlay-opacity': 0.14,
    } as Css.Node,
  },
  {
    selector: 'node[severity = "high"]',
    style: {
      'border-color': '#ff7a18',
      'overlay-color': '#ff7a18',
      'overlay-opacity': 0.1,
    } as Css.Node,
  },
  {
    selector: '.focus',
    style: {
      'border-width': 4.5,
      'border-color': '#33dcff',
      'overlay-color': '#33dcff',
      'overlay-opacity': 0.18,
      width: 80,
      height: 80,
      'z-index': 999,
    } as Css.Node,
  },
  {
    selector: 'edge',
    style: {
      'curve-style': 'bezier',
      'control-point-step-size': 60,
      'line-color': 'data(color)',
      'target-arrow-color': 'data(color)',
      'target-arrow-shape': 'triangle',
      'arrow-scale': 1,
      width: 2,
      opacity: 0.75,
      'line-cap': 'round',
      label: 'data(type)',
      color: '#8b98b6',
      'font-family': '"JetBrains Mono Variable", ui-monospace, monospace',
      'font-size': 8,
      'text-rotation': 'autorotate',
      'text-background-color': '#0a0e14',
      'text-background-opacity': 0.7,
      'text-background-padding': '2',
    } as Css.Edge,
  },
  {
    selector: 'edge.focus',
    style: { width: 3.4, opacity: 1 } as Css.Edge,
  },
];

function shorten(s: string, max: number): string {
  if (s.length <= max) return s;
  return `${s.slice(0, max - 1)}…`;
}

type Reduced = {
  nodes: CyNode[];
  edges: CyEdge[];
  clusterMembers: Map<string, ClusterMembers[]>;
};

// Drop redundant Target -> Vulnerability edge when Endpoint -> Vulnerability
// edge already exists (vuln semantically attached to endpoint).
// Then fold sibling leaves of same (parent, label, rel_type) into a cluster
// node so the attack-path renders close to one-line.
function reduceGraph(data: AttackSurfaceResp, highlightId: string | null): Reduced {
  const nodeById = new Map(data.nodes.map((n) => [n.data.id, n]));
  let edges = data.edges.slice();

  // 1) Drop redundant Target -> V edge if Endpoint -> V exists.
  const endpointVulnTargets = new Set<string>();
  edges.forEach((e) => {
    if (e.data.type !== 'HAS_VULN') return;
    const src = nodeById.get(e.data.source);
    if (src?.data.label === 'Endpoint') endpointVulnTargets.add(e.data.target);
  });
  edges = edges.filter((e) => {
    if (e.data.type !== 'HAS_VULN') return true;
    const src = nodeById.get(e.data.source);
    if (src?.data.label !== 'Target') return true;
    return !endpointVulnTargets.has(e.data.target);
  });

  // 2) Compute degrees on the trimmed edge set.
  const outDeg = new Map<string, number>();
  const inEdges = new Map<string, CyEdge[]>();
  edges.forEach((e) => {
    outDeg.set(e.data.source, (outDeg.get(e.data.source) ?? 0) + 1);
    if (!inEdges.has(e.data.target)) inEdges.set(e.data.target, []);
    inEdges.get(e.data.target)!.push(e);
  });

  // 3) Group leaves: out-degree 0, in-degree 1, not the highlighted finding.
  const groups = new Map<string, string[]>();
  data.nodes.forEach((n) => {
    if (n.data.id === highlightId) return;
    const out = outDeg.get(n.data.id) ?? 0;
    const inc = inEdges.get(n.data.id) ?? [];
    if (out !== 0 || inc.length !== 1) return;
    const e = inc[0]!;
    const key = `${e.data.source}|${n.data.label}|${e.data.type}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(n.data.id);
  });

  const clustered = new Set<string>();
  const clusterMembers = new Map<string, ClusterMembers[]>();
  const clusterNodes: CyNode[] = [];
  const clusterEdges: CyEdge[] = [];

  groups.forEach((ids, key) => {
    if (ids.length < 2) return;
    const parts = key.split('|');
    const parent = parts[0] ?? '';
    const label = parts[1] ?? '';
    const relType = parts[2] ?? '';
    ids.forEach((id) => clustered.add(id));
    const cid = `cluster::${parent}::${label}::${relType}`;
    clusterNodes.push({
      data: {
        id: cid,
        label,
        display: `${TYPE_HINT[label] ?? label}s (${ids.length})`,
        severity: null,
        cvss: null,
      },
    } as unknown as CyNode);
    clusterEdges.push({
      data: {
        id: `${parent}--${relType}-->${cid}`,
        source: parent,
        target: cid,
        type: relType,
      },
    });
    clusterMembers.set(
      cid,
      ids.map((id) => {
        const m = nodeById.get(id);
        return {
          id,
          display: m?.data.display || id,
          severity: m?.data.severity ?? null,
          cvss: m?.data.cvss ?? null,
        };
      })
    );
  });

  const remainingNodes = data.nodes.filter((n) => !clustered.has(n.data.id));
  const remainingEdges = edges.filter(
    (e) => !clustered.has(e.data.source) && !clustered.has(e.data.target)
  );

  return {
    nodes: [...remainingNodes, ...clusterNodes],
    edges: [...remainingEdges, ...clusterEdges],
    clusterMembers,
  };
}

function buildAttackPathElements(
  reduced: Reduced,
  highlightId?: string | null
): ElementDefinition[] {
  const nodeIds = new Set(reduced.nodes.map((n) => n.data.id));
  const nodes: ElementDefinition[] = reduced.nodes.map((n: CyNode) => {
    const isCluster = n.data.id.startsWith('cluster::');
    const ring = SEV_RING[n.data.severity ?? ''] ?? NODE_BORDER[n.data.label] ?? '#4cc9f0';
    const name = shorten(n.data.display || n.data.id, 28);
    const type = TYPE_HINT[n.data.label] ?? n.data.label;
    return {
      group: 'nodes',
      data: {
        id: n.data.id,
        label: n.data.label,
        display: isCluster ? name : `${name}\n${type}`,
        severity: n.data.severity ?? '',
        cvss: n.data.cvss ?? '',
        ring,
        shape: NODE_SHAPE[n.data.label] ?? 'round-rectangle',
        fill: NODE_FILL[n.data.label] ?? '#0d131c',
        isCluster: isCluster ? '1' : '0',
      },
      classes: highlightId && n.data.id === highlightId ? 'focus' : '',
    };
  });
  const edges: ElementDefinition[] = reduced.edges
    .filter((e: CyEdge) => nodeIds.has(e.data.source) && nodeIds.has(e.data.target))
    .map((e) => ({
      group: 'edges',
      data: { ...e.data, color: EDGE_COLOR[e.data.type] ?? '#37445a' },
      classes:
        highlightId && (e.data.source === highlightId || e.data.target === highlightId)
          ? 'focus'
          : '',
    }));
  return [...nodes, ...edges];
}

export function MiniGraph({
  data,
  height = 320,
  highlightId,
  fill = false,
}: {
  data: AttackSurfaceResp;
  height?: number;
  highlightId?: string | null;
  fill?: boolean;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const [selected, setSelected] = useState<SelectedNode | null>(null);

  const reduced = useMemo<Reduced>(() => {
    const r = reduceGraph(data, highlightId ?? null);
    if (expanded.size === 0) return r;
    // Re-expand selected clusters: drop cluster node, restore members & their incoming edge.
    const keepNodes: CyNode[] = [];
    const keepEdges: CyEdge[] = [];
    const restored = new Set<string>();
    r.nodes.forEach((n) => {
      if (n.data.id.startsWith('cluster::') && expanded.has(n.data.id)) {
        const members = r.clusterMembers.get(n.data.id) ?? [];
        const parts = n.data.id.split('::');
        const parent = parts[1] ?? '';
        const relType = parts[3] ?? '';
        members.forEach((m) => {
          const orig = data.nodes.find((dn) => dn.data.id === m.id);
          if (orig) keepNodes.push(orig);
          keepEdges.push({
            data: {
              id: `${parent}--${relType}-->${m.id}`,
              source: parent,
              target: m.id,
              type: relType,
            },
          });
          restored.add(m.id);
        });
        return;
      }
      keepNodes.push(n);
    });
    r.edges.forEach((e) => {
      if (e.data.source.startsWith('cluster::') && expanded.has(e.data.source)) return;
      if (e.data.target.startsWith('cluster::') && expanded.has(e.data.target)) return;
      keepEdges.push(e);
    });
    return { nodes: keepNodes, edges: keepEdges, clusterMembers: r.clusterMembers };
  }, [data, highlightId, expanded]);

  useEffect(() => {
    ensureExtensionRegistered();
    if (!containerRef.current) return;
    const elements = buildAttackPathElements(reduced, highlightId);

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: STYLE,
      layout: {
        name: 'dagre',
        rankDir: 'LR',
        ranker: 'longest-path',
        nodeSep: 70,
        rankSep: 170,
        edgeSep: 30,
        animate: false,
        padding: 50,
      } as unknown as cytoscape.LayoutOptions,
      wheelSensitivity: 0.2,
      minZoom: 0.4,
      maxZoom: 2.5,
    });
    cyRef.current = cy;

    cy.fit(undefined, 40);
    if (highlightId) {
      const target = cy.getElementById(highlightId);
      if (target.nonempty()) cy.center(target);
    }

    cy.on('tap', 'node', (e) => {
      const n = e.target;
      const id = n.id();
      const raw = reduced.nodes.find((rn) => rn.data.id === id);
      if (!raw) return;
      const isCluster = id.startsWith('cluster::');
      setSelected({
        id,
        label: raw.data.label,
        type: TYPE_HINT[raw.data.label] ?? raw.data.label,
        display: raw.data.display || id,
        severity: raw.data.severity ?? undefined,
        cvss: raw.data.cvss ?? undefined,
        isCluster,
        members: isCluster ? reduced.clusterMembers.get(id) : undefined,
        ring: SEV_RING[raw.data.severity ?? ''] ?? NODE_BORDER[raw.data.label] ?? '#4cc9f0',
      });
    });
    cy.on('tap', (e) => {
      if (e.target === cy) setSelected(null);
    });

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [reduced, highlightId]);

  const toggleCluster = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setSelected(null);
  };

  return (
    <div
      style={fill ? undefined : { height }}
      className={`relative w-full overflow-hidden rounded border border-bg-line bg-bg-base ${
        fill ? 'h-full' : ''
      }`}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.08]"
        style={{
          backgroundImage: 'radial-gradient(circle at 1px 1px, #6b7a90 1px, transparent 0)',
          backgroundSize: '18px 18px',
        }}
      />
      <div ref={containerRef} className="relative h-full w-full" />
      {selected && (
        <NodeDetailCard
          selected={selected}
          onClose={() => setSelected(null)}
          onToggleCluster={toggleCluster}
          isClusterExpanded={selected.isCluster && expanded.has(selected.id)}
        />
      )}
    </div>
  );
}

function severityTone(sev?: string): string {
  switch (sev) {
    case 'critical':
      return '#ff3860';
    case 'high':
      return '#ff7a18';
    case 'medium':
      return '#ffb000';
    case 'low':
      return '#2dd4bf';
    case 'info':
      return '#4cc9f0';
    default:
      return '#6b7a90';
  }
}

function NodeDetailCard({
  selected,
  onClose,
  onToggleCluster,
  isClusterExpanded,
}: {
  selected: SelectedNode;
  onClose: () => void;
  onToggleCluster: (id: string) => void;
  isClusterExpanded: boolean;
}) {
  const sevColor = severityTone(selected.severity);
  return (
    <div className="absolute right-3 top-3 z-10 w-[320px] max-w-[90%] overflow-hidden rounded-lg border border-bg-line bg-bg-base/95 shadow-xl backdrop-blur">
      <div
        className="flex items-center justify-between gap-2 border-b border-bg-line px-3 py-2"
        style={{
          background: `linear-gradient(90deg, ${selected.ring}24 0%, transparent 100%)`,
          borderLeftWidth: 3,
          borderLeftColor: selected.ring,
        }}
      >
        <span className="text-2xs font-mono uppercase tracking-wider text-text-muted">
          {selected.type}
          {selected.isCluster && selected.members ? ` · ${selected.members.length} items` : ''}
        </span>
        <button
          type="button"
          onClick={onClose}
          className="text-text-muted hover:text-text-primary"
          aria-label="Close"
        >
          ×
        </button>
      </div>
      <div className="px-3 py-2.5">
        <div className="mb-2 break-words text-sm font-medium text-text-primary">
          {selected.display}
        </div>
        <dl className="space-y-1.5 font-mono text-2xs">
          {selected.severity && (
            <div className="flex items-center justify-between gap-3">
              <dt className="text-text-muted">severity</dt>
              <dd
                className="rounded px-1.5 py-0.5 text-2xs uppercase"
                style={{ color: sevColor, background: `${sevColor}1f` }}
              >
                {selected.severity}
              </dd>
            </div>
          )}
          {selected.cvss !== undefined && selected.cvss !== '' && (
            <div className="flex items-center justify-between gap-3">
              <dt className="text-text-muted">cvss</dt>
              <dd className="text-text-primary">{String(selected.cvss)}</dd>
            </div>
          )}
          <div className="flex items-start justify-between gap-3">
            <dt className="text-text-muted">id</dt>
            <dd className="break-all text-right text-text-secondary">{selected.id}</dd>
          </div>
        </dl>
        {selected.isCluster && selected.members && (
          <div className="mt-3 space-y-2">
            <button
              type="button"
              onClick={() => onToggleCluster(selected.id)}
              className="ra-btn ra-btn-ghost ra-btn-sm w-full justify-center"
            >
              {isClusterExpanded ? 'Collapse cluster' : 'Expand cluster'}
            </button>
            <ul className="max-h-40 overflow-y-auto rounded border border-bg-line/60 bg-bg-base/50 p-1.5 font-mono text-2xs">
              {selected.members.map((m) => (
                <li
                  key={m.id}
                  className="flex items-center justify-between gap-2 rounded px-1.5 py-1 text-text-secondary hover:bg-bg-overlay"
                >
                  <span className="truncate">{m.display}</span>
                  {m.severity && (
                    <span
                      className="shrink-0 rounded px-1 text-2xs uppercase"
                      style={{
                        color: severityTone(m.severity),
                        background: `${severityTone(m.severity)}1f`,
                      }}
                    >
                      {m.severity}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
