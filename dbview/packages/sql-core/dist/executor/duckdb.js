import { DuckDBInstance } from '@duckdb/node-api';
export class DuckdbExecutor {
    filePath;
    instance;
    connection;
    constructor(filePath) {
        this.filePath = filePath;
    }
    async getConnection() {
        if (!this.connection) {
            this.instance = await DuckDBInstance.create(this.filePath, { access_mode: 'READ_ONLY' });
            this.connection = await this.instance.connect();
        }
        return this.connection;
    }
    async run(sql, rowLimit) {
        const start = performance.now();
        const conn = await this.getConnection();
        const reader = await conn.runAndReadAll(sql);
        const columns = reader.columnNames();
        const allRows = reader.getRowsJS();
        const truncated = allRows.length > rowLimit;
        return {
            columns,
            rows: allRows.slice(0, rowLimit),
            rowCount: Math.min(allRows.length, rowLimit),
            durationMs: Math.round(performance.now() - start),
            truncated,
        };
    }
    async close() {
        if (this.connection) {
            this.connection.closeSync();
            this.connection = undefined;
        }
        if (this.instance) {
            this.instance.closeSync();
            this.instance = undefined;
        }
    }
}
//# sourceMappingURL=duckdb.js.map