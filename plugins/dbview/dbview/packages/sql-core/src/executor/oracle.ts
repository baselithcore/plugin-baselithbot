import oracledb from 'oracledb';
import type { ExecuteQueryResponse } from '@dbview/shared';
import type { QueryExecutor } from './types.js';
import { parseOracleUrl } from './oracle-url.js';

export class OracleExecutor implements QueryExecutor {
  private readonly cfg: oracledb.ConnectionAttributes;
  private pool: oracledb.Pool | undefined;

  constructor(connectionString: string) {
    this.cfg = parseOracleUrl(connectionString);
  }

  private async getPool(): Promise<oracledb.Pool> {
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

  async run(sql: string, rowLimit: number): Promise<ExecuteQueryResponse> {
    const pool = await this.getPool();
    const conn = await pool.getConnection();
    const start = performance.now();
    try {
      await conn.execute('SET TRANSACTION READ ONLY');
      const res = await conn.execute<unknown[]>(sql, [], {
        outFormat: oracledb.OUT_FORMAT_ARRAY,
        maxRows: rowLimit + 1,
        resultSet: false,
      });
      await conn.commit();
      const rawRows = (res.rows ?? []) as unknown[][];
      const truncated = rawRows.length > rowLimit;
      const columns = (res.metaData ?? []).map((m) => m.name);
      return {
        columns,
        rows: rawRows.slice(0, rowLimit),
        rowCount: Math.min(rawRows.length, rowLimit),
        durationMs: Math.round(performance.now() - start),
        truncated,
      };
    } finally {
      await conn.close();
    }
  }

  async close(): Promise<void> {
    if (this.pool) {
      await this.pool.close(0);
      this.pool = undefined;
    }
  }
}
