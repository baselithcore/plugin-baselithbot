import mysqlPkg from 'mysql2/promise';
import type { ExecuteQueryResponse } from '@dbview/shared';
import type { QueryExecutor } from './types.js';

const { createPool } = mysqlPkg;

export class MysqlExecutor implements QueryExecutor {
  private readonly pool: ReturnType<typeof createPool>;

  constructor(connectionString: string) {
    this.pool = createPool({
      uri: connectionString,
      connectionLimit: 4,
      waitForConnections: true,
      timezone: 'Z',
      multipleStatements: false,
    });
  }

  async run(sql: string, rowLimit: number): Promise<ExecuteQueryResponse> {
    const conn = await this.pool.getConnection();
    const start = performance.now();
    try {
      await conn.query('SET SESSION TRANSACTION READ ONLY');
      await conn.query('SET SESSION MAX_EXECUTION_TIME = 5000');
      const [rowsRaw, fieldsRaw] = await conn.query({ sql, rowsAsArray: true });
      const rows = rowsRaw as unknown[][];
      const fields = (fieldsRaw ?? []) as Array<{ name: string }>;
      const truncated = rows.length >= rowLimit;
      return {
        columns: fields.map((f) => f.name),
        rows: rows.slice(0, rowLimit),
        rowCount: rows.length,
        durationMs: Math.round(performance.now() - start),
        truncated,
      };
    } finally {
      conn.release();
    }
  }

  async close(): Promise<void> {
    await this.pool.end();
  }
}
