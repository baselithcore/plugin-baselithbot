import { DuckDBInstance, type DuckDBConnection } from '@duckdb/node-api';
import type { ExecuteQueryResponse } from '@dbview/shared';
import type { QueryExecutor } from './types.js';

export class DuckdbExecutor implements QueryExecutor {
  private instance: DuckDBInstance | undefined;
  private connection: DuckDBConnection | undefined;

  constructor(private readonly filePath: string) {}

  private async getConnection(): Promise<DuckDBConnection> {
    if (!this.connection) {
      this.instance = await DuckDBInstance.create(this.filePath, { access_mode: 'READ_ONLY' });
      this.connection = await this.instance.connect();
    }
    return this.connection;
  }

  async run(sql: string, rowLimit: number): Promise<ExecuteQueryResponse> {
    const start = performance.now();
    const conn = await this.getConnection();
    const reader = await conn.runAndReadAll(sql);
    const columns = reader.columnNames();
    const allRows = reader.getRowsJS() as unknown[][];
    const truncated = allRows.length > rowLimit;
    return {
      columns,
      rows: allRows.slice(0, rowLimit),
      rowCount: Math.min(allRows.length, rowLimit),
      durationMs: Math.round(performance.now() - start),
      truncated,
    };
  }

  async close(): Promise<void> {
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
