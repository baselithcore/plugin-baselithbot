import { fetchPage } from './api';

/**
 * Cache module-level di pagine già fetchate. Condivisa tra
 * CitationPopover (hover) e SourcesDrawer (click) per non duplicare
 * round-trip e mostrare istantaneamente l'excerpt al secondo hover.
 */
interface CachedPage {
  document_id: string;
  title: string;
  body: string;
  obsidian_uri?: string | null;
}

const cache = new Map<string, CachedPage>();
const inflight = new Map<string, Promise<CachedPage>>();

export function getCachedPage(docId: string): CachedPage | null {
  return cache.get(docId) ?? null;
}

export function loadPage(docId: string, signal?: AbortSignal): Promise<CachedPage> {
  const hit = cache.get(docId);
  if (hit) return Promise.resolve(hit);
  const flying = inflight.get(docId);
  if (flying) return flying;
  const p = fetchPage(docId, signal).then((p) => {
    const entry: CachedPage = {
      document_id: p.document_id,
      title: p.title,
      body: p.body,
      obsidian_uri: p.obsidian_uri ?? null,
    };
    cache.set(docId, entry);
    inflight.delete(docId);
    return entry;
  });
  inflight.set(docId, p);
  p.catch(() => inflight.delete(docId));
  return p;
}
