import type { ExecuteQueryResponse } from '@dbview/shared';

function isGraphEntity(v: unknown): boolean {
  if (!v || typeof v !== 'object') return false;
  const k = (v as { _kind?: unknown })._kind;
  return k === 'node' || k === 'relationship';
}

/** True when at least one cell across rows is a graph node or relationship. */
export function resultHasGraph(result: ExecuteQueryResponse): boolean {
  for (const row of result.rows) {
    for (const v of row) {
      if (isGraphEntity(v)) return true;
    }
  }
  return false;
}
