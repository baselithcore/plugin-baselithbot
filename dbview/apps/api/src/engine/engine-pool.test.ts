import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { applySqliteSqlDump } from '@dbview/sql-core';
import { EnginePool } from './engine-pool.js';

let tmpDir: string;
let dbPath: string;

beforeAll(() => {
  tmpDir = mkdtempSync(join(tmpdir(), 'dbview-enginepool-'));
  dbPath = join(tmpDir, 'fixture.db');
  applySqliteSqlDump(
    dbPath,
    "CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT); INSERT INTO t (name) VALUES ('a');"
  );
});

afterAll(() => {
  rmSync(tmpDir, { recursive: true, force: true });
});

describe('EnginePool', () => {
  it('returns the same engine for repeated acquires of an SQL dialect', () => {
    const pool = new EnginePool();
    try {
      const a = pool.acquire('sqlite', dbPath);
      const b = pool.acquire('sqlite', dbPath);
      expect(a).not.toBeNull();
      expect(a).toBe(b);
    } finally {
      void pool.onModuleDestroy();
    }
  });

  it('returns null for non-SQL dialects', () => {
    const pool = new EnginePool();
    try {
      expect(pool.acquire('neo4j', 'neo4j://localhost:7687')).toBeNull();
      expect(pool.acquire('qdrant', 'http://localhost:6333')).toBeNull();
    } finally {
      void pool.onModuleDestroy();
    }
  });

  it('invalidate evicts the entry; subsequent acquire produces a fresh engine', () => {
    const pool = new EnginePool();
    try {
      const a = pool.acquire('sqlite', dbPath);
      pool.invalidate('sqlite', dbPath);
      const b = pool.acquire('sqlite', dbPath);
      expect(a).not.toBe(b);
    } finally {
      void pool.onModuleDestroy();
    }
  });

  it('onModuleDestroy closes all engines and clears the cache', async () => {
    const pool = new EnginePool();
    pool.acquire('sqlite', dbPath);
    await pool.onModuleDestroy();
    const fresh = pool.acquire('sqlite', dbPath);
    expect(fresh).not.toBeNull();
    await pool.onModuleDestroy();
  });
});
