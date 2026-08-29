import oracledb from 'oracledb';
import { parseOracleUrl } from './oracle-url.js';
export class OracleExecutor {
    cfg;
    pool;
    constructor(connectionString) {
        this.cfg = parseOracleUrl(connectionString);
    }
    async getPool() {
        if (!this.pool) {
            this.pool = await oracledb.createPool({
                ...this.cfg,
                poolMin: 0,
                poolMax: 4,
                poolIncrement: 1,
            });
        }
        return this.pool;
    }
    async run(sql, rowLimit) {
        const pool = await this.getPool();
        const conn = await pool.getConnection();
        const start = performance.now();
        try {
            await conn.execute('SET TRANSACTION READ ONLY');
            const res = await conn.execute(sql, [], {
                outFormat: oracledb.OUT_FORMAT_ARRAY,
                maxRows: rowLimit + 1,
                resultSet: false,
            });
            await conn.commit();
            const rawRows = (res.rows ?? []);
            const truncated = rawRows.length > rowLimit;
            const columns = (res.metaData ?? []).map((m) => m.name);
            return {
                columns,
                rows: rawRows.slice(0, rowLimit),
                rowCount: Math.min(rawRows.length, rowLimit),
                durationMs: Math.round(performance.now() - start),
                truncated,
            };
        }
        finally {
            await conn.close();
        }
    }
    async close() {
        if (this.pool) {
            await this.pool.close(0);
            this.pool = undefined;
        }
    }
}
//# sourceMappingURL=oracle.js.map