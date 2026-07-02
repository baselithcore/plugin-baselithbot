import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import type { CreateHistoryEntryDto } from '@dbview/shared';
import { HistoryStore } from './history.store.js';

const OWNER_A = '00000000-0000-0000-0000-0000000000aa';
const OWNER_B = '00000000-0000-0000-0000-0000000000bb';

let dir: string;
let store: HistoryStore;

function makeDto(overrides: Partial<CreateHistoryEntryDto> = {}): CreateHistoryEntryDto {
  return {
    connectionId: '00000000-0000-0000-0000-000000000001',
    connectionName: 'demo',
    prompt: 'top 5 customers',
    query: 'SELECT id FROM customers LIMIT 5',
    language: 'sql',
    provider: 'ollama',
    model: 'llama3',
    summary: null,
    rowCount: 5,
    durationMs: 12,
    ok: true,
    errorCode: null,
    errorMessage: null,
    ...overrides,
  };
}

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), 'dbview-history-'));
  store = new HistoryStore(join(dir, 'history.json'));
});

afterEach(() => {
  rmSync(dir, { recursive: true, force: true });
});

describe('HistoryStore', () => {
  it('creates entries with id, ownerId and createdAt', () => {
    const entry = store.create(makeDto(), OWNER_A);
    expect(entry.id).toMatch(/^[0-9a-f-]{36}$/);
    expect(entry.ownerId).toBe(OWNER_A);
    expect(entry.favorite).toBe(false);
    expect(entry.createdAt).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  });

  it('lists entries newest first, scoped by owner', async () => {
    const a = store.create(makeDto({ prompt: 'first' }), OWNER_A);
    await new Promise((r) => setTimeout(r, 5));
    const b = store.create(makeDto({ prompt: 'second' }), OWNER_A);
    const out = store.list({ limit: 10, offset: 0 }, OWNER_A);
    expect(out.total).toBe(2);
    expect(out.entries[0]!.id).toBe(b.id);
    expect(out.entries[1]!.id).toBe(a.id);
  });

  it('hides entries owned by another user', () => {
    store.create(makeDto({ prompt: 'mine' }), OWNER_A);
    store.create(makeDto({ prompt: 'theirs' }), OWNER_B);
    const out = store.list({ limit: 10, offset: 0 }, OWNER_A);
    expect(out.total).toBe(1);
    expect(out.entries[0]!.prompt).toBe('mine');
  });

  it('filters by connectionId', () => {
    store.create(makeDto({ connectionId: '00000000-0000-0000-0000-000000000001' }), OWNER_A);
    store.create(makeDto({ connectionId: '00000000-0000-0000-0000-000000000002' }), OWNER_A);
    const out = store.list(
      {
        connectionId: '00000000-0000-0000-0000-000000000002',
        limit: 10,
        offset: 0,
      },
      OWNER_A
    );
    expect(out.total).toBe(1);
    expect(out.entries[0]!.connectionId).toBe('00000000-0000-0000-0000-000000000002');
  });

  it('filters favoritesOnly', () => {
    const a = store.create(makeDto({ prompt: 'a' }), OWNER_A);
    store.create(makeDto({ prompt: 'b' }), OWNER_A);
    store.setFavorite(a.id, true);
    const out = store.list({ favoritesOnly: true, limit: 10, offset: 0 }, OWNER_A);
    expect(out.total).toBe(1);
    expect(out.entries[0]!.prompt).toBe('a');
  });

  it('paginates with limit and offset', () => {
    for (let i = 0; i < 5; i++) store.create(makeDto({ prompt: `q${i}` }), OWNER_A);
    const page1 = store.list({ limit: 2, offset: 0 }, OWNER_A);
    const page2 = store.list({ limit: 2, offset: 2 }, OWNER_A);
    expect(page1.entries).toHaveLength(2);
    expect(page2.entries).toHaveLength(2);
    expect(page1.entries[0]!.id).not.toBe(page2.entries[0]!.id);
  });

  it('toggles favorite via setFavorite', () => {
    const e = store.create(makeDto(), OWNER_A);
    const updated = store.setFavorite(e.id, true);
    expect(updated?.favorite).toBe(true);
    const backOff = store.setFavorite(e.id, false);
    expect(backOff?.favorite).toBe(false);
  });

  it('setFavorite returns undefined for unknown id', () => {
    expect(store.setFavorite('missing', true)).toBeUndefined();
  });

  it('removes an entry', () => {
    const e = store.create(makeDto(), OWNER_A);
    expect(store.remove(e.id)).toBe(true);
    expect(store.get(e.id)).toBeUndefined();
    expect(store.remove(e.id)).toBe(false);
  });

  it('clear() removes non-favorite entries but preserves starred, scoped by owner', () => {
    const a = store.create(makeDto({ prompt: 'keep me' }), OWNER_A);
    store.create(makeDto({ prompt: 'drop me' }), OWNER_A);
    store.create(makeDto({ prompt: 'other user' }), OWNER_B);
    store.setFavorite(a.id, true);
    const out = store.clear(OWNER_A);
    expect(out).toBe(1);
    expect(store.list({ limit: 10, offset: 0 }, OWNER_A).total).toBe(1);
    expect(store.list({ limit: 10, offset: 0 }, OWNER_B).total).toBe(1);
  });

  it('clear() scoped by connectionId', () => {
    store.create(makeDto({ connectionId: '00000000-0000-0000-0000-000000000001' }), OWNER_A);
    store.create(makeDto({ connectionId: '00000000-0000-0000-0000-000000000002' }), OWNER_A);
    store.clear(OWNER_A, '00000000-0000-0000-0000-000000000001');
    const remaining = store.list({ limit: 10, offset: 0 }, OWNER_A);
    expect(remaining.total).toBe(1);
    expect(remaining.entries[0]!.connectionId).toBe('00000000-0000-0000-0000-000000000002');
  });

  it('persists across instances at the same path', () => {
    const path = join(dir, 'persisted.json');
    const s1 = new HistoryStore(path);
    s1.create(makeDto({ prompt: 'persisted' }), OWNER_A);
    const s2 = new HistoryStore(path);
    expect(s2.list({ limit: 10, offset: 0 }, OWNER_A).total).toBe(1);
  });

  it('ignores a corrupt JSON file rather than crashing', () => {
    const path = join(dir, 'corrupt.json');
    writeFileSync(path, 'not json {{{');
    const s = new HistoryStore(path);
    expect(s.list({ limit: 10, offset: 0 }, OWNER_A).total).toBe(0);
  });

  it('marks legacy entries without ownerId as pending backfill', () => {
    const path = join(dir, 'legacy.json');
    writeFileSync(
      path,
      JSON.stringify({
        version: 1,
        entries: [
          {
            id: '00000000-0000-0000-0000-0000000000ff',
            connectionId: '00000000-0000-0000-0000-000000000001',
            connectionName: 'old',
            prompt: 'legacy',
            query: 'SELECT 1',
            language: 'sql',
            provider: 'ollama',
            model: 'm',
            summary: null,
            rowCount: null,
            durationMs: null,
            ok: true,
            errorCode: null,
            errorMessage: null,
            favorite: false,
            createdAt: '2025-01-01T00:00:00.000Z',
          },
        ],
      })
    );
    const s = new HistoryStore(path);
    expect(s.pendingLegacyIds()).toHaveLength(1);
    s.reassignOwner('00000000-0000-0000-0000-0000000000ff', OWNER_A);
    expect(s.pendingLegacyIds()).toHaveLength(0);
    expect(s.list({ limit: 10, offset: 0 }, OWNER_A).total).toBe(1);
  });
});
