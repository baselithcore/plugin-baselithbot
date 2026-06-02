/**
 * Knowledge-graph API client (graphify PR3).
 *
 * Mirrors the FastAPI surface under `/api/graph/*`. Endpoints requiring
 * a live FalkorDB return 503 when offline; this module surfaces that as
 * a typed `GraphUnavailableError` so the UI can render a "graph: off"
 * banner instead of an error toast.
 */

import { ApiError, json } from './client';

export class GraphUnavailableError extends Error {
  constructor(message = 'Knowledge graph not available') {
    super(message);
    this.name = 'GraphUnavailableError';
  }
}

export interface GraphStats {
  enabled: boolean;
  nodes: number;
  edges: number;
  entities: number;
  mentions: number;
  relations: number;
}

export interface GraphNode {
  id: string;
  name: string;
  kind: string;
  pagerank: number;
  degree: number;
  community: number;
}

export interface GraphEdge {
  src: string;
  dst: string;
  kind: string;
  confidence: number;
}

export interface GraphCommunity {
  id: number;
  size: number;
  cohesion: number;
  members: string[];
}

export interface SurprisingEdge {
  src: string;
  dst: string;
  kind: string;
  confidence: number;
  src_community: number;
  dst_community: number;
}

export interface GraphData {
  enabled: boolean;
  generated_at?: string;
  stats: { node_count: number; edge_count: number; community_count: number };
  nodes: GraphNode[];
  edges: GraphEdge[];
  communities: GraphCommunity[];
  surprising: SurprisingEdge[];
}

export interface EntityRecord {
  id: string;
  name: string;
  kind: string;
  aliases: string[];
}

export interface EntitySearchResponse {
  query: string;
  kind: string | null;
  count: number;
  results: EntityRecord[];
}

export interface NeighborsResponse {
  entity_id: string;
  hops: number;
  confidence_min: number;
  count: number;
  results: EntityRecord[];
}

async function _get<T>(path: string): Promise<T> {
  try {
    return await json<T>(path);
  } catch (err) {
    if (err instanceof ApiError && err.status === 503) {
      throw new GraphUnavailableError();
    }
    throw err;
  }
}

export function getStats(): Promise<GraphStats> {
  return _get<GraphStats>('/graph/stats');
}

export function getData(opts?: {
  confidence_min?: number;
  resolution?: number;
  top_n?: number;
  max_nodes?: number;
}): Promise<GraphData> {
  const params = new URLSearchParams();
  if (opts?.confidence_min !== undefined) params.set('confidence_min', String(opts.confidence_min));
  if (opts?.resolution !== undefined) params.set('resolution', String(opts.resolution));
  if (opts?.top_n !== undefined) params.set('top_n', String(opts.top_n));
  if (opts?.max_nodes !== undefined) params.set('max_nodes', String(opts.max_nodes));
  const qs = params.toString();
  return _get<GraphData>(`/graph/data${qs ? `?${qs}` : ''}`);
}

export function searchEntities(
  q: string,
  opts?: { kind?: string; limit?: number }
): Promise<EntitySearchResponse> {
  const params = new URLSearchParams({ q });
  if (opts?.kind) params.set('kind', opts.kind);
  if (opts?.limit !== undefined) params.set('limit', String(opts.limit));
  return _get<EntitySearchResponse>(`/graph/search?${params.toString()}`);
}

export function getEntity(id: string): Promise<EntityRecord> {
  return _get<EntityRecord>(`/graph/entity/${encodeURIComponent(id)}`);
}

export function getNeighbors(
  id: string,
  opts?: { hops?: number; confidence_min?: number; kind?: string; limit?: number }
): Promise<NeighborsResponse> {
  const params = new URLSearchParams();
  if (opts?.hops !== undefined) params.set('hops', String(opts.hops));
  if (opts?.confidence_min !== undefined) params.set('confidence_min', String(opts.confidence_min));
  if (opts?.kind) params.set('kind', opts.kind);
  if (opts?.limit !== undefined) params.set('limit', String(opts.limit));
  const qs = params.toString();
  return _get<NeighborsResponse>(`/graph/neighbors/${encodeURIComponent(id)}${qs ? `?${qs}` : ''}`);
}
