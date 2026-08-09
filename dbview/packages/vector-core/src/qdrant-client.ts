import { IntrospectionError } from '@dbview/shared';
import type { QdrantTarget } from './parse.js';

export interface QdrantCollectionInfo {
  status: string;
  vectors_count?: number;
  points_count?: number;
  config: {
    params: {
      vectors:
        { size: number; distance: string } | Record<string, { size: number; distance: string }>;
    };
  };
}

export interface QdrantPoint {
  id: string | number;
  payload?: Record<string, unknown>;
  vector?: number[] | Record<string, number[]>;
}

const REQUEST_TIMEOUT_MS = 15_000;

/**
 * Minimal Qdrant HTTP client over `fetch`.
 *
 * Avoids depending on `@qdrant/js-client-rest` to keep the package small —
 * we only need a handful of read-only endpoints (collections list/get, scroll, search).
 */
export class QdrantClient {
  constructor(private readonly target: QdrantTarget) {}

  async listCollections(): Promise<string[]> {
    const res = await this.request<{
      result: { collections: Array<{ name: string }> };
    }>('GET', '/collections');
    return res.result.collections.map((c) => c.name);
  }

  async getCollection(name: string): Promise<QdrantCollectionInfo> {
    const res = await this.request<{ result: QdrantCollectionInfo }>(
      'GET',
      `/collections/${encodeURIComponent(name)}`
    );
    return res.result;
  }

  async countPoints(name: string, filter?: Record<string, unknown>): Promise<number> {
    const body: Record<string, unknown> = { exact: true };
    if (filter) body.filter = filter;
    const res = await this.request<{ result: { count: number } }>(
      'POST',
      `/collections/${encodeURIComponent(name)}/points/count`,
      body
    );
    return res.result.count;
  }

  async scroll(
    name: string,
    limit: number,
    withPayload = true,
    withVector = false,
    filter?: Record<string, unknown>
  ): Promise<QdrantPoint[]> {
    const body: Record<string, unknown> = {
      limit,
      with_payload: withPayload,
      with_vector: withVector,
    };
    if (filter) body.filter = filter;
    const res = await this.request<{
      result: { points: QdrantPoint[]; next_page_offset?: unknown };
    }>('POST', `/collections/${encodeURIComponent(name)}/points/scroll`, body);
    return res.result.points ?? [];
  }

  async search(
    name: string,
    vector: number[],
    opts: {
      limit?: number;
      usingNamedVector?: string;
      withPayload?: boolean;
      filter?: Record<string, unknown>;
    } = {}
  ): Promise<Array<{ id: string | number; score: number; payload?: Record<string, unknown> }>> {
    const body: Record<string, unknown> = {
      vector: opts.usingNamedVector ? { name: opts.usingNamedVector, vector } : vector,
      limit: opts.limit ?? 20,
      with_payload: opts.withPayload ?? true,
    };
    if (opts.filter) body.filter = opts.filter;
    const res = await this.request<{
      result: Array<{ id: string | number; score: number; payload?: Record<string, unknown> }>;
    }>('POST', `/collections/${encodeURIComponent(name)}/points/search`, body);
    return res.result;
  }

  async ping(): Promise<void> {
    // `/healthz` is the lightweight readiness check exposed by recent Qdrant versions.
    // Fall back to listing collections if that endpoint is missing.
    try {
      await this.request('GET', '/healthz');
    } catch {
      await this.listCollections();
    }
  }

  private async request<T>(method: 'GET' | 'POST', path: string, body?: unknown): Promise<T> {
    const url = `${this.target.baseUrl}${path}`;
    const headers: Record<string, string> = { 'content-type': 'application/json' };
    if (this.target.apiKey) headers['api-key'] = this.target.apiKey;
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), REQUEST_TIMEOUT_MS);
    try {
      const res = await fetch(url, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: ctrl.signal,
      });
      const text = await res.text();
      if (!res.ok) {
        throw new IntrospectionError(
          `Qdrant ${method} ${path} → ${res.status}: ${text.slice(0, 200) || res.statusText}`
        );
      }
      if (!text) return {} as T;
      return JSON.parse(text) as T;
    } catch (err) {
      if ((err as { name?: string }).name === 'AbortError') {
        throw new IntrospectionError(
          `Qdrant ${method} ${path} timed out after ${REQUEST_TIMEOUT_MS}ms`
        );
      }
      if (err instanceof IntrospectionError) throw err;
      throw new IntrospectionError(`Qdrant ${method} ${path} failed: ${(err as Error).message}`);
    } finally {
      clearTimeout(timer);
    }
  }
}
