import Database from 'better-sqlite3';
export class SqliteExecutor {
    db;
    constructor(filePath) {
        this.db = new Database(filePath, { readonly: true, fileMustExist: true });
        this.db.pragma('query_only = ON');
    }
    async run(sql, rowLimit) {
        const start = performance.now();
        const stmt = this.db.prepare(sql);
        stmt.raw(true);
        const rows = stmt.all();
        const cols = stmt.columns().map((c) => c.name);
        const truncated = rows.length >= rowLimit;
        return {
            columns: cols,
            rows: rows.slice(0, rowLimit),
            rowCount: rows.length,
            durationMs: Math.round(performance.now() - start),
            truncated,
        };
    }
    async close() {
        this.db.close();
    }
}
//# sourceMappingURL=sqlite.js.map