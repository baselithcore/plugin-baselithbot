import Database from 'better-sqlite3';
import type { ExecuteQueryResponse } from '@dbview/shared';
import type { QueryExecutor } from './types.js';

export class SqliteExecutor implements QueryExecutor {
  private readonly db: Database.Database;

  constructor(filePath: string) {
    this.db = new Database(filePath, { readonly: true, fileMustExist: true });
    this.db.pragma('query_only = ON');
  }

  async run(sql: string, rowLimit: number): Promise<ExecuteQueryResponse> {
    const start = performance.now();
    const stmt = this.db.prepare(sql);
    stmt.raw(true);
    const rows = stmt.all() as unknown[][];
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

  async close(): Promise<void> {
    this.db.close();
  }
}
