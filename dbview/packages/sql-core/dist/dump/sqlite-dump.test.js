import { describe, it, expect, afterEach } from 'vitest';
import { mkdtempSync, rmSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import Database from 'better-sqlite3';
import { applySqliteSqlDump, isSqliteDatabaseBuffer, writeSqliteDbFile } from './sqlite-dump.js';
const tmpDirs = [];
function mkTmp() {
    const d = mkdtempSync(join(tmpdir(), 'dbview-dump-'));
    tmpDirs.push(d);
    return d;
}
function runBatch(db, sql) {
    const fn = db['exec'];
    fn.call(db, sql);
}
afterEach(() => {
    while (tmpDirs.length) {
        const d = tmpDirs.pop();
        rmSync(d, { recursive: true, force: true });
    }
});
describe('isSqliteDatabaseBuffer', () => {
    it('detects valid magic header', () => {
        const buf = Buffer.alloc(100);
        Buffer.from([
            0x53, 0x51, 0x4c, 0x69, 0x74, 0x65, 0x20, 0x66, 0x6f, 0x72, 0x6d, 0x61, 0x74, 0x20, 0x33,
            0x00,
        ]).copy(buf, 0);
        expect(isSqliteDatabaseBuffer(buf)).toBe(true);
    });
    it('rejects random bytes', () => {
        expect(isSqliteDatabaseBuffer(Buffer.from('not a db'))).toBe(false);
    });
});
describe('writeSqliteDbFile', () => {
    it('writes and validates a real sqlite db', () => {
        const dir = mkTmp();
        const seedPath = join(dir, 'seed.db');
        const seed = new Database(seedPath);
        runBatch(seed, "CREATE TABLE t (id INTEGER PRIMARY KEY, n TEXT); INSERT INTO t (n) VALUES ('a');");
        seed.close();
        const buf = readFileSync(seedPath);
        const target = join(dir, 'out.db');
        writeSqliteDbFile(target, buf);
        const db = new Database(target, { readonly: true });
        const row = db.prepare('SELECT n FROM t WHERE id = 1').get();
        db.close();
        expect(row.n).toBe('a');
    });
    it('rejects non-sqlite buffer', () => {
        const dir = mkTmp();
        expect(() => writeSqliteDbFile(join(dir, 'x.db'), Buffer.from('garbage'))).toThrow(/not a valid SQLite/);
    });
});
describe('applySqliteSqlDump', () => {
    it('creates db from sql dump and reports table count', () => {
        const dir = mkTmp();
        const target = join(dir, 'from-dump.db');
        const sql = `
      CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT);
      CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER);
      INSERT INTO users (email) VALUES ('a@b.c');
    `;
        const res = applySqliteSqlDump(target, sql);
        expect(res.tables).toBe(2);
        const db = new Database(target, { readonly: true });
        const n = db.prepare('SELECT count(*) AS c FROM users').get().c;
        db.close();
        expect(n).toBe(1);
    });
    it('throws if dump produces no tables', () => {
        const dir = mkTmp();
        expect(() => applySqliteSqlDump(join(dir, 'empty.db'), 'SELECT 1;')).toThrow(/did not create any tables/);
    });
    it('throws on empty dump', () => {
        const dir = mkTmp();
        expect(() => applySqliteSqlDump(join(dir, 'e.db'), '   ')).toThrow(/empty/);
    });
    it('rejects Postgres dump with a clear hint', () => {
        const dir = mkTmp();
        const pgDump = `--
-- PostgreSQL database dump
--
SET statement_timeout = 0;
SET client_encoding = 'UTF8';
CREATE TABLE public.users (id integer NOT NULL);
`;
        expect(() => applySqliteSqlDump(join(dir, 'pg.db'), pgDump)).toThrow(/PostgreSQL dump/);
    });
    it('refuses to overwrite existing target', () => {
        const dir = mkTmp();
        const target = join(dir, 'pre.db');
        applySqliteSqlDump(target, 'CREATE TABLE a (x INTEGER);');
        expect(() => applySqliteSqlDump(target, 'CREATE TABLE b (y INTEGER);')).toThrow(/already exists/);
    });
});
//# sourceMappingURL=sqlite-dump.test.js.map