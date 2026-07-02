import mssql from 'mssql';
import type { ExecuteQueryResponse } from '@dbview/shared';
import type { QueryExecutor } from './types.js';

export class MssqlExecutor implements QueryExecutor {
  private readonly poolPromise: Promise<mssql.ConnectionPool>;

  constructor(connectionString: string) {
    const pool = new mssql.ConnectionPool(connectionString);
    this.poolPromise = pool.connect();
  }

  async run(sql: string, rowLimit: number): Promise<ExecuteQueryResponse> {
    const pool = await this.poolPromise;
    const start = performance.now();
    const req = pool.request();
    req.arrayRowMode = true;
    const res = (await req.query(sql)) as unknown as {
      recordset?: { columns: Record<string, { name: string }> } & unknown[][];
      recordsets?: Array<{ columns: Record<string, { name: string }> } & unknown[][]>;
    };
    const recordset = res.recordset ?? res.recordsets?.[0];
    const rowsArr = (recordset ?? []) as unknown as unknown[][];
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

  async close(): Promise<void> {
    const pool = await this.poolPromise;
    await pool.close();
  }
}
