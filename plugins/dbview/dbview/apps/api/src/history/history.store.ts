import { randomUUID } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import type { CreateHistoryEntryDto, HistoryEntry, ListHistoryQuery } from '@dbview/shared';

type RawHistoryEntry = Partial<HistoryEntry> & { id: string };

interface FileShape {
  version: 1;
  entries: RawHistoryEntry[];
}

function defaultPath(): string {
  return resolve(process.env.DBVIEW_DATA_DIR ?? './data', 'history.json');
}
const MAX_ENTRIES = Number(process.env.DBVIEW_HISTORY_MAX) || 5000;

/**
 * JSON-file store for NL2Query history + favorites. Mirrors the
 * ConnectionsStore pattern: in-memory map, atomic write, tmp+rename.
 *
 * Each entry carries an `ownerId` — list/clear filter strictly by owner so
 * users only ever see their own history. Pre-tenant-isolation entries
 * without `ownerId` are backfilled to the first admin on boot (same as
 * `ConnectionsStore`).
 *
 * Entries are capped at MAX_ENTRIES; non-favorite oldest entries get
 * evicted first so a starred query is never lost to rotation.
 */
export class HistoryStore {
  private entries: Map<string, HistoryEntry> = new Map();
  private legacyIds: Set<string> = new Set();
  // Secondary index for owner-scoped list/clear so we never walk every
  // entry across the install when only one user's slice is needed.
  private byOwner: Map<string, Set<string>> = new Map();
  private readonly filePath: string;

  constructor(filePath?: string) {
    this.filePath = filePath ?? defaultPath();
    this.load();
  }

  list(query: ListHistoryQuery, ownerId: string): { entries: HistoryEntry[]; total: number } {
    const ids = this.byOwner.get(ownerId);
    if (!ids || ids.size === 0) return { entries: [], total: 0 };
    const arr: HistoryEntry[] = [];
    for (const id of ids) {
      const e = this.entries.get(id);
      if (!e) continue;
      if (query.connectionId && e.connectionId !== query.connectionId) continue;
      if (query.favoritesOnly && !e.favorite) continue;
      arr.push(e);
    }
    arr.sort((a, b) => (a.createdAt < b.createdAt ? 1 : a.createdAt > b.createdAt ? -1 : 0));
    const total = arr.length;
    const sliced = arr.slice(query.offset, query.offset + query.limit);
    return { entries: sliced, total };
  }

  get(id: string): HistoryEntry | undefined {
    return this.entries.get(id);
  }

  create(dto: CreateHistoryEntryDto, ownerId: string): HistoryEntry {
    const entry: HistoryEntry = {
      ...dto,
      id: randomUUID(),
      ownerId,
      favorite: false,
      createdAt: new Date().toISOString(),
    };
    this.entries.set(entry.id, entry);
    this.indexAdd(entry);
    this.evictIfOver();
    this.persist();
    return entry;
  }

  setFavorite(id: string, favorite: boolean): HistoryEntry | undefined {
    const existing = this.entries.get(id);
    if (!existing) return undefined;
    const updated: HistoryEntry = { ...existing, favorite };
    this.entries.set(id, updated);
    this.persist();
    return updated;
  }

  remove(id: string): boolean {
    const existing = this.entries.get(id);
    if (!existing) return false;
    this.entries.delete(id);
    this.indexRemove(existing);
    this.persist();
    return true;
  }

  clear(ownerId: string, connectionId?: string): number {
    const ids = this.byOwner.get(ownerId);
    if (!ids || ids.size === 0) return 0;
    let removed = 0;
    for (const id of [...ids]) {
      const e = this.entries.get(id);
      if (!e) continue;
      if (connectionId && e.connectionId !== connectionId) continue;
      if (e.favorite) continue; // never wipe starred entries
      this.entries.delete(id);
      this.indexRemove(e);
      removed += 1;
    }
    if (removed > 0) this.persist();
    return removed;
  }

  /**
   * Admin-only nuke: wipe every entry across all users, including favorites.
   * Bypasses the owner scope. Used by `DELETE /api/history/all`.
   */
  clearAll(): number {
    const n = this.entries.size;
    if (n === 0) return 0;
    this.entries.clear();
    this.byOwner.clear();
    this.legacyIds.clear();
    this.persist();
    return n;
  }

  pendingLegacyIds(): string[] {
    return [...this.legacyIds];
  }

  reassignOwner(id: string, ownerId: string): void {
    const existing = this.entries.get(id);
    if (!existing) return;
    this.indexRemove(existing);
    const updated = { ...existing, ownerId };
    this.entries.set(id, updated);
    this.indexAdd(updated);
    this.legacyIds.delete(id);
    this.persist();
  }

  private indexAdd(e: HistoryEntry): void {
    let bucket = this.byOwner.get(e.ownerId);
    if (!bucket) {
      bucket = new Set();
      this.byOwner.set(e.ownerId, bucket);
    }
    bucket.add(e.id);
  }

  private indexRemove(e: HistoryEntry): void {
    const bucket = this.byOwner.get(e.ownerId);
    if (!bucket) return;
    bucket.delete(e.id);
    if (bucket.size === 0) this.byOwner.delete(e.ownerId);
  }

  private evictIfOver(): void {
    if (this.entries.size <= MAX_ENTRIES) return;
    const candidates = [...this.entries.values()]
      .filter((e) => !e.favorite)
      .sort((a, b) => (a.createdAt < b.createdAt ? -1 : 1));
    const overflow = this.entries.size - MAX_ENTRIES;
    for (let i = 0; i < overflow && i < candidates.length; i++) {
      const victim = candidates[i]!;
      this.entries.delete(victim.id);
      this.indexRemove(victim);
    }
  }

  private load(): void {
    if (!existsSync(this.filePath)) return;
    try {
      const raw = readFileSync(this.filePath, 'utf8');
      const data = JSON.parse(raw) as FileShape;
      if (data.version !== 1 || !Array.isArray(data.entries)) return;
      for (const e of data.entries) {
        const isLegacy = !e.ownerId;
        if (isLegacy) this.legacyIds.add(e.id);
        const filled: HistoryEntry = {
          id: e.id,
          ownerId: e.ownerId ?? `legacy:${e.id}`,
          connectionId: e.connectionId!,
          connectionName: e.connectionName ?? '',
          prompt: e.prompt ?? '',
          query: e.query ?? '',
          language: e.language!,
          provider: e.provider ?? '',
          model: e.model ?? '',
          summary: e.summary ?? null,
          rowCount: e.rowCount ?? null,
          durationMs: e.durationMs ?? null,
          ok: e.ok ?? false,
          errorCode: e.errorCode ?? null,
          errorMessage: e.errorMessage ?? null,
          favorite: e.favorite ?? false,
          createdAt: e.createdAt ?? new Date().toISOString(),
        };
        this.entries.set(filled.id, filled);
        this.indexAdd(filled);
      }
    } catch {
      // Ignore corrupt file; start fresh rather than crash on boot.
    }
  }

  private persist(): void {
    const dir = dirname(this.filePath);
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    const tmp = `${this.filePath}.tmp`;
    const data: FileShape = { version: 1, entries: [...this.entries.values()] };
    writeFileSync(tmp, JSON.stringify(data, null, 2), { mode: 0o600 });
    renameSync(tmp, this.filePath);
  }
}
