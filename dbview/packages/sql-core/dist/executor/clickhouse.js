import { createClient } from '@clickhouse/client';
export class ClickhouseExecutor {
    connectionString;
    client;
    constructor(connectionString) {
        this.connectionString = connectionString;
    }
    getClient() {
        if (!this.client) {
            this.client = createClient({
                url: this.connectionString,
                request_timeout: 5_000,
                application: 'dbview-executor',
                // Force server-side read-only mode (level 1 = no writes, no settings change).
                clickhouse_settings: { readonly: '1' },
            });
        }
        return this.client;
    }
    async run(sql, rowLimit) {
        const start = performance.now();
        const client = this.getClient();
        const rs = await client.query({ query: sql, format: 'JSONCompactEachRowWithNamesAndTypes' });
        const stream = await rs.json();
        const arr = stream;
        // First element = column names, second = column types, rest = rows.
        const columns = Array.isArray(arr[0]) ? arr[0] : [];
        const dataRows = arr.slice(2);
        const truncated = dataRows.length > rowLimit;
        return {
            columns,
            rows: dataRows.slice(0, rowLimit),
            rowCount: Math.min(dataRows.length, rowLimit),
            durationMs: Math.round(performance.now() - start),
            truncated,
        };
    }
    async close() {
        if (this.client) {
            await this.client.close();
            this.client = undefined;
        }
    }
}
//# sourceMappingURL=clickhouse.js.map