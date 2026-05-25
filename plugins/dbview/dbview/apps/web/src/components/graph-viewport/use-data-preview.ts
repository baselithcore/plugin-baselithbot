import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { ExecuteQueryResponse, UnifiedSchema } from '@dbview/shared';
import { api } from '../../lib/api.js';

const GRAPH_NODES_PREVIEW_QUERY = 'MATCH (n) RETURN n';
const GRAPH_EDGES_PREVIEW_QUERY = 'MATCH (a)-[r]->(b) RETURN a, r, b';
const DATA_PREVIEW_LIMIT = 2000;

export const DATA_PREVIEW_QUERY_KEY = 'graph-data-preview';

export function useDataPreview(
  connId: string | null,
  schema: UnifiedSchema | undefined,
  enabled: boolean
) {
  const previewKind = schema?.kind ?? null;
  const vectorPreviewQuery = useMemo(() => {
    if (schema?.kind !== 'vector') return null;
    const first = schema.collections[0];
    if (!first) return null;
    return JSON.stringify({
      op: 'scroll',
      collection: first.name,
      limit: DATA_PREVIEW_LIMIT,
      withPayload: true,
    });
  }, [schema]);

  const query = useQuery({
    queryKey: [DATA_PREVIEW_QUERY_KEY, connId, previewKind, vectorPreviewQuery],
    queryFn: async (): Promise<ExecuteQueryResponse> => {
      if (previewKind === 'graph') {
        // Two parallel queries: not every GQL dialect honours OPTIONAL MATCH
        // the same way (Ultipa returns isolated nodes but skips edge traversal
        // when used in a single MATCH ... OPTIONAL MATCH chain). Run nodes
        // and edges as separate statements and merge into one result.
        const [nodes, edges] = await Promise.all([
          api.execute({
            connectionId: connId!,
            query: GRAPH_NODES_PREVIEW_QUERY,
            rowLimit: DATA_PREVIEW_LIMIT,
          }),
          api
            .execute({
              connectionId: connId!,
              query: GRAPH_EDGES_PREVIEW_QUERY,
              rowLimit: DATA_PREVIEW_LIMIT,
            })
            .catch(() => null),
        ]);
        return {
          columns: ['n', 'r', 'm'],
          rows: [
            ...nodes.rows.map((row) => [row[0], null, null] as unknown[]),
            ...(edges?.rows ?? []).map((row) => [row[0], row[1], row[2]] as unknown[]),
          ],
          rowCount: nodes.rowCount + (edges?.rowCount ?? 0),
          durationMs: nodes.durationMs + (edges?.durationMs ?? 0),
          truncated: nodes.truncated || (edges?.truncated ?? false),
        };
      }
      return api.execute({
        connectionId: connId!,
        query: vectorPreviewQuery!,
        rowLimit: DATA_PREVIEW_LIMIT,
      });
    },
    enabled:
      !!connId &&
      enabled &&
      (previewKind === 'graph' || (previewKind === 'vector' && !!vectorPreviewQuery)),
    staleTime: 30_000,
  });

  const counts = useMemo(() => {
    if (!query.data) return null;
    const nodeIds = new Set<string>();
    let edges = 0;
    for (const row of query.data.rows) {
      for (const v of row) {
        if (v && typeof v === 'object') {
          const k = (v as { _kind?: string })._kind;
          if (k === 'node') {
            const id = (v as { id?: unknown; _id?: unknown }).id ?? (v as { _id?: unknown })._id;
            if (id !== undefined) nodeIds.add(String(id));
          } else if (k === 'relationship') {
            edges++;
          }
        }
      }
    }
    return { nodes: nodeIds.size, edges };
  }, [query.data]);

  return { query, counts };
}
