import type { EditionMeta, Status, WikiPageMeta } from '../types';
import { ApiError, BASE, json } from './client';

export function fetchStatus(signal?: AbortSignal): Promise<Status> {
  return json<Status>('/status', { signal });
}

export function fetchPages(
  signal?: AbortSignal
): Promise<{ count: number; pages: WikiPageMeta[] }> {
  return json('/wiki/pages', { signal });
}

export async function fetchEditions(
  signal?: AbortSignal
): Promise<{ count: number; editions: EditionMeta[] }> {
  // Generic engine: editions are now a grouping rule. If the active
  // pack does not declare one we return empty rather than 404.
  try {
    const r = await json<{
      count: number;
      groups: Array<{
        id: string;
        label: string;
        key: Record<string, string>;
        extras: Record<string, string | null>;
      }>;
    }>('/groups/editions', { signal });
    const editions: EditionMeta[] = r.groups.map((g) => ({
      id: g.id,
      label: g.label,
      edizione: g.key.edizione ?? '',
      edizione_iso: g.key['edizione-iso'] ?? g.extras['edizione-iso'] ?? '',
      stato: (g.extras.stato as EditionMeta['stato']) ?? 'vigente',
      note: g.extras.note ?? '',
      codice_prodotto: g.extras.codice_prodotto ?? null,
      modello: g.extras.modello ?? null,
      sources: [],
    }));
    return { count: editions.length, editions };
  } catch (err) {
    if (err instanceof ApiError && (err.status === 404 || err.status === 503)) {
      return { count: 0, editions: [] };
    }
    throw err;
  }
}

export function fetchPage(docId: string, signal?: AbortSignal) {
  return json<{
    document_id: string;
    title: string;
    type: string;
    body: string;
    category: string;
    tags: string[];
    wikilinks_out: string[];
    relative_path?: string;
    obsidian_uri?: string | null;
  }>(`/wiki/page/${encodeURIComponent(docId)}`, { signal });
}

export function reindexAll(): Promise<{ status: string; count: number; total_chunks: number }> {
  return json('/ingest', { method: 'POST' });
}

/**
 * Costruisci URL diretto al raw file servito dal backend
 * (``GET /api/raw/file/{name}``). Accetta valori frontmatter come
 * ``"raw/contract-44.pdf"`` o ``"contract-44.pdf"``; estrae basename.
 *
 * Per PDF, append ``#page=N`` per deep-link nativo del browser.
 */
export function rawFileUrl(sourceFile: string, page?: number): string {
  const name = sourceFile.replace(/^.*[/\\]/, '');
  const safe = encodeURIComponent(name);
  const url = `${BASE}/raw/file/${safe}`;
  return page && page > 0 ? `${url}#page=${page}` : url;
}
