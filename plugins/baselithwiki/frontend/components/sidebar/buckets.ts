import type { Conversation } from '../../lib/types';

export type Bucket = { label: string; items: Conversation[] };

export function bucketize(convs: Conversation[]): Bucket[] {
  const now = new Date();
  const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const yesterday = startOfDay - 86_400_000;
  const sevenDaysAgo = startOfDay - 7 * 86_400_000;
  const thirtyDaysAgo = startOfDay - 30 * 86_400_000;

  const buckets: Record<string, Conversation[]> = {
    oggi: [],
    ieri: [],
    'ultimi 7 giorni': [],
    'ultimi 30 giorni': [],
    'più vecchi': [],
  };

  const sorted = [...convs].sort((a, b) => b.updatedAt - a.updatedAt);
  for (const c of sorted) {
    if (c.updatedAt >= startOfDay) buckets.oggi.push(c);
    else if (c.updatedAt >= yesterday) buckets.ieri.push(c);
    else if (c.updatedAt >= sevenDaysAgo) buckets['ultimi 7 giorni'].push(c);
    else if (c.updatedAt >= thirtyDaysAgo) buckets['ultimi 30 giorni'].push(c);
    else buckets['più vecchi'].push(c);
  }

  return Object.entries(buckets)
    .filter(([, items]) => items.length > 0)
    .map(([label, items]) => ({ label, items }));
}

export function matchesQuery(c: Conversation, q: string): boolean {
  if (!q) return true;
  const needle = q.toLowerCase();
  if (c.title.toLowerCase().includes(needle)) return true;
  return c.messages.some((m) => m.content.toLowerCase().includes(needle));
}
