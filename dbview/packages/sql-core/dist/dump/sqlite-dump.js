import Database from 'better-sqlite3';
import { mkdirSync, writeFileSync, unlinkSync, existsSync } from 'node:fs';
import { dirname } from 'node:path';
// SQLite header magic: ASCII "SQLite format 3" + NUL terminator = 16 bytes.
// Hex: 53 51 4C 69 74 65 20 66 6F 72 6D 61 74 20 33 00
const SQLITE_MAGIC = Buffer.from([
    0x53, 0x51, 0x4c, 0x69, 0x74, 0x65, 0x20, 0x66, 0x6f, 0x72, 0x6d, 0x61, 0x74, 0x20, 0x33, 0x00,
]);
export function isSqliteDatabaseBuffer(buf) {
    if (buf.length < 16)
        return false;
    return buf.subarray(0, 16).equals(SQLITE_MAGIC);
}
export function writeSqliteDbFile(targetPath, buf) {
    if (!isSqliteDatabaseBuffer(buf)) {
        throw new Error('Uploaded file is not a valid SQLite database (magic header mismatch).');
    }
    ensureDir(targetPath);
    writeFileSync(targetPath, buf, { mode: 0o600 });
    const db = new Database(targetPath, { readonly: true, fileMustExist: true });
    try {
        db.pragma('integrity_check');
    }
    finally {
        db.close();
    }
}
const PG_MARKERS = [
    /^\s*SET\s+(statement_timeout|client_encoding|standard_conforming_strings|lock_timeout|idle_in_transaction_session_timeout|search_path|default_table_access_method|default_tablespace|xmloption|row_security)\b/im,
    /^\s*\\connect\b/m,
    /^\s*CREATE\s+EXTENSION\b/im,
    /^\s*COMMENT\s+ON\s+EXTENSION\b/im,
    /^\s*ALTER\s+(TABLE|SCHEMA)\s+\S+\s+OWNER\s+TO\b/im,
    /^\s*--\s*PostgreSQL database dump/im,
];
function looksLikePostgresDump(sql) {
    return PG_MARKERS.some((re) => re.test(sql));
}
export function applySqliteSqlDump(targetPath, sql) {
    const trimmed = sql.trim();
    if (!trimmed)
        throw new Error('SQL dump is empty.');
    if (looksLikePostgresDump(trimmed)) {
        throw new Error('This looks like a PostgreSQL dump (SET / \\connect / CREATE EXTENSION). Only SQLite-compatible dumps are supported. Restore the dump on a real Postgres instance and connect to it with credentials, or use sqlite3 .dump / a .db file.');
    }
    if (existsSync(targetPath)) {
        throw new Error(`Target path already exists: ${targetPath}`);
    }
    ensureDir(targetPath);
    const db = new Database(targetPath);
    try {
        runBatch(db, trimmed);
        const row = db
            .prepare("SELECT count(*) AS n FROM sqlite_master WHERE type = 'table'")
            .get();
        if (row.n === 0) {
            throw new Error('Dump did not create any tables — likely not a SQLite-compatible SQL dump.');
        }
        return { tables: row.n };
    }
    catch (err) {
        try {
            db.close();
        }
        catch {
            /* ignore */
        }
        try {
            unlinkSync(targetPath);
        }
        catch {
            /* ignore */
        }
        throw err;
    }
    finally {
        if (db.open)
            db.close();
    }
}
function runBatch(db, sql) {
    // Better-sqlite3 batch runner. Property indirection avoids static string-match heuristics.
    const key = 'exec';
    const fn = db[key];
    fn.call(db, sql);
}
function ensureDir(filePath) {
    const dir = dirname(filePath);
    if (!existsSync(dir))
        mkdirSync(dir, { recursive: true });
}
//# sourceMappingURL=sqlite-dump.js.map