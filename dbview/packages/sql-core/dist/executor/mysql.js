import mysqlPkg from 'mysql2/promise';
const { createPool } = mysqlPkg;
export class MysqlExecutor {
    pool;
    constructor(connectionString) {
        this.pool = createPool({
            uri: connectionString,
            connectionLimit: 4,
            waitForConnections: true,
            timezone: 'Z',
            multipleStatements: false,
        });
    }
    async run(sql, rowLimit) {
        const conn = await this.pool.getConnection();
        const start = performance.now();
        try {
            await conn.query('SET SESSION TRANSACTION READ ONLY');
            await conn.query('SET SESSION MAX_EXECUTION_TIME = 5000');
            const [rowsRaw, fieldsRaw] = await conn.query({ sql, rowsAsArray: true });
            const rows = rowsRaw;
            const fields = (fieldsRaw ?? []);
            const truncated = rows.length >= rowLimit;
            return {
                columns: fields.map((f) => f.name),
                rows: rows.slice(0, rowLimit),
                rowCount: rows.length,
                durationMs: Math.round(performance.now() - start),
                truncated,
            };
        }
        finally {
            conn.release();
        }
    }
    async close() {
        await this.pool.end();
    }
}
//# sourceMappingURL=mysql.js.map