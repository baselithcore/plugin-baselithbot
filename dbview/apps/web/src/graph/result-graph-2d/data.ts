import type { ExecuteQueryResponse } from '@dbview/shared';
import { colorForKey } from '../palette.js';
import type { NodeShape, RelShape, ResLink, ResNode } from './types.js';

export function isNode(v: unknown): v is NodeShape {
  return !!v && typeof v === 'object' && (v as { _kind?: unknown })._kind === 'node';
}

export function isRel(v: unknown): v is RelShape {
  return !!v && typeof v === 'object' && (v as { _kind?: unknown })._kind === 'relationship';
}

export function nodeId(n: NodeShape): string {
  const id = n.id ?? n._id ?? n.uid;
  if (id !== undefined) return `${n._labels[0] ?? 'Node'}:${String(id)}`;
  return `${n._labels[0] ?? 'Node'}:${JSON.stringify(n).slice(0, 32)}`;
}

export function nodeDisplay(n: NodeShape): string {
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

export function buildGraphData(result: ExecuteQueryResponse): {
  nodes: ResNode[];
  links: ResLink[];
} {
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
          if (origId !== undefined && (typeof origId === 'string' || typeof origId === 'number')) {
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
}

const RESERVED_KEYS = new Set(['_kind', '_labels', '_schema', '_id', '_uuid', '_fromId', '_toId']);

export function extractProperties(raw: NodeShape): Array<[string, unknown]> {
  const out: Array<[string, unknown]> = [];
  for (const [k, v] of Object.entries(raw)) {
    if (RESERVED_KEYS.has(k)) continue;
    out.push([k, v]);
  }
  return out;
}

export function formatValue(v: unknown): string {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'string') return v;
  if (typeof v === 'number' || typeof v === 'boolean') return String(v);
  try {
    return JSON.stringify(v, null, 2);
  } catch {
    return String(v);
  }
}
