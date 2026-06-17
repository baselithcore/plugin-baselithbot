// Shared graph styling — single source of truth for both the 2D and 3D
// renderers so node/edge colors stay identical across views.
import type { GraphData } from '@/lib/types';

export const NODE_COLORS: Record<string, string> = {
  note: '#8b5cf6',
  tag: '#22d3ee',
  moc: '#f59e0b',
};
export const ACTIVE_COLOR = '#ec4899';

export const EDGE_COLORS: Record<string, string> = {
  explicit: 'rgba(130,130,160,0.42)',
  derived: 'rgba(139,92,246,0.42)',
  tag: 'rgba(34,211,238,0.34)',
};

export interface RenderProps {
  data: GraphData;
  activeId?: string | null;
  width: number;
  height: number;
  onNode: (id: string) => void;
}

export function nodeColor(node: { id: string; kind: string }, activeId?: string | null): string {
  return node.id === activeId ? ACTIVE_COLOR : NODE_COLORS[node.kind] || NODE_COLORS.note;
}

export function edgeColor(link: { kind?: string }): string {
  return EDGE_COLORS[link.kind || 'explicit'] || EDGE_COLORS.explicit;
}

// ForceGraph mutates node/link objects in place; clone so React state stays
// immutable across re-renders.
export function cloneGraph(data: GraphData) {
  return {
    nodes: data.nodes.map((n) => ({ ...n })),
    links: data.edges.map((e) => ({ ...e })),
  };
}
