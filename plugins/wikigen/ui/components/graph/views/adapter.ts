import type { GraphData, GraphEdge, GraphNode } from '../../../lib/api/graph';

export interface FGNode {
  id: string;
  name: string;
  kind: string;
  community: number;
  pagerank: number;
  degree: number;
  val: number;
  color: string;
  // Injected by the force-graph engine after the first tick.
  x?: number;
  y?: number;
  z?: number;
}

export interface FGLink {
  source: string;
  target: string;
  kind: string;
  confidence: number;
}

export interface FGData {
  nodes: FGNode[];
  links: FGLink[];
  neighborsById: Map<string, Set<string>>;
  degreeById: Map<string, number>;
}

// Tailwind-friendly community palette. Index 0 reserved for orphans (community < 0).
const COMMUNITY_COLOURS = [
  '#94a3b8',
  '#3b82f6',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#ec4899',
  '#14b8a6',
  '#f97316',
  '#06b6d4',
  '#84cc16',
  '#a855f7',
] as const;

export function communityColour(community: number): string {
  if (community < 0) return COMMUNITY_COLOURS[0];
  return COMMUNITY_COLOURS[(community + 1) % COMMUNITY_COLOURS.length];
}

// PageRank distribution is heavily right-skewed; log-scale prevents one
// god-node from dwarfing the rest. Returns force-graph nodeVal (size proxy).
export function nodeVal(pagerank: number, degree: number): number {
  const logged = Math.log10(1 + Math.max(0, pagerank) * 1000);
  const base = 4 + logged * 3;
  return base + Math.sqrt(Math.max(0, degree)) * 0.6;
}

/**
 * Builds force-graph ready node/link arrays from the API GraphData. Applies
 * filter masks (kinds + communities + min confidence + search) by mutating
 * only the per-node/per-edge `color` returned via accessors — we do NOT
 * remove elements, so the simulation does not reheat on filter changes.
 *
 * Returns precomputed neighbor adjacency for the hover-highlight path.
 */
export interface BuildOptions {
  visibleKinds: Set<string>;
  visibleCommunities: Set<number>;
  confidenceMin: number;
}

export function buildFGData(data: GraphData, _opts: BuildOptions): FGData {
  const nodeIds = new Set<string>(data.nodes.map((n) => n.id));
  const degreeById = new Map<string, number>();
  const neighborsById = new Map<string, Set<string>>();

  for (const e of data.edges) {
    if (!nodeIds.has(e.src) || !nodeIds.has(e.dst)) continue;
    degreeById.set(e.src, (degreeById.get(e.src) ?? 0) + 1);
    degreeById.set(e.dst, (degreeById.get(e.dst) ?? 0) + 1);
    if (!neighborsById.has(e.src)) neighborsById.set(e.src, new Set());
    if (!neighborsById.has(e.dst)) neighborsById.set(e.dst, new Set());
    neighborsById.get(e.src)!.add(e.dst);
    neighborsById.get(e.dst)!.add(e.src);
  }

  const nodes: FGNode[] = data.nodes.map<FGNode>((n: GraphNode) => ({
    id: n.id,
    name: n.name,
    kind: n.kind,
    community: n.community,
    pagerank: n.pagerank,
    degree: degreeById.get(n.id) ?? n.degree ?? 0,
    val: nodeVal(n.pagerank, degreeById.get(n.id) ?? n.degree ?? 0),
    color: communityColour(n.community),
  }));

  const links: FGLink[] = data.edges
    .filter((e: GraphEdge) => nodeIds.has(e.src) && nodeIds.has(e.dst))
    .map<FGLink>((e) => ({
      source: e.src,
      target: e.dst,
      kind: e.kind,
      confidence: e.confidence,
    }));

  return { nodes, links, neighborsById, degreeById };
}

/**
 * Returns true when the node passes the active filter set. Used by the views
 * via colour-dimming (no remount). Empty filter set = "no filter applied"
 * (consistent with GraphFilters semantics).
 */
export function isNodeVisible(node: FGNode, opts: BuildOptions, search: string): boolean {
  const kindOk = opts.visibleKinds.size === 0 || opts.visibleKinds.has(node.kind);
  const commOk = opts.visibleCommunities.size === 0 || opts.visibleCommunities.has(node.community);
  if (!kindOk || !commOk) return false;
  const q = search.trim().toLowerCase();
  if (!q) return true;
  return node.name.toLowerCase().includes(q);
}

export function isLinkVisible(
  link: FGLink,
  visibleNodeIds: Set<string>,
  confidenceMin: number
): boolean {
  if (link.confidence < confidenceMin) return false;
  const src = typeof link.source === 'object' ? (link.source as FGNode).id : link.source;
  const tgt = typeof link.target === 'object' ? (link.target as FGNode).id : link.target;
  return visibleNodeIds.has(src) && visibleNodeIds.has(tgt);
}

export const DIMMED_NODE = '#3a3f4a';
export const DIMMED_LINK = '#2a2f3a';

export function edgeBaseColor(): string {
  return '#94a3b8';
}

// Edge width by confidence (linear 0.6→3.0px). Picked-up by both 2D and 3D
// renderers; the hover-highlight path scales further on top of this baseline.
export function edgeBaseWidth(confidence: number): number {
  return Math.max(0.6, Math.min(3.0, 0.6 + confidence * 2.4));
}

/**
 * Resolves a link endpoint id whether the force-graph engine has already
 * replaced the string with the live node object (post-first-tick) or not.
 */
export function linkEndpointId(end: string | object): string {
  return typeof end === 'object' ? (end as FGNode).id : (end as string);
}
