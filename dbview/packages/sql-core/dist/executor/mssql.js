import mssql from 'mssql';
export class MssqlExecutor {
    poolPromise;
    constructor(connectionString) {
        const pool = new mssql.ConnectionPool(connectionString);
        this.poolPromise = pool.connect();
    }
    async run(sql, rowLimit) {
        const pool = await this.poolPromise;
        const start = performance.now();
        const req = pool.request();
        req.arrayRowMode = true;
        const res = (await req.query(sql));
        const recordset = res.recordset ?? res.recordsets?.[0];
        const rowsArr = (recordset ?? []);
        const colsMeta = recordset?.columns ?? {};
        const columns = Object.values(colsMeta).map((c) => c.name);
        const rows = rowsArr;
        const truncated = rows.length >= rowLimit;
        return {
            columns,
            rows: rows.slice(0, rowLimit),
            rowCount: rows.length,
            durationMs: Math.round(performance.now() - start),
            truncated,
        };
    }
    async close() {
        const pool = await this.poolPromise;
        await pool.close();
    }
}
//# sourceMappingURL=mssql.js.map