import pg from 'pg';
import type { Pool as PgPool, FieldDef } from 'pg';
import type { ExecuteQueryResponse } from '@dbview/shared';
import type { QueryExecutor } from './types.js';

const { Pool } = pg;

export class PostgresExecutor implements QueryExecutor {
  private readonly pool: PgPool;

  constructor(connectionString: string) {
    this.pool = new Pool({
      connectionString,
      max: 4,
      statement_timeout: 5_000,
      application_name: 'dbview-executor',
    });
  }

  async run(sql: string, rowLimit: number): Promise<ExecuteQueryResponse> {
    const client = await this.pool.connect();
    const start = performance.now();
    try {
      await client.query('BEGIN READ ONLY');
      const nsRes = await client.query<{ nspname: string }>(
        `SELECT nspname FROM pg_namespace
         WHERE nspname NOT LIKE 'pg\\_%' ESCAPE '\\'
           AND nspname <> 'information_schema'
         ORDER BY nspname`
      );
      const schemas = nsRes.rows.map((r) => `"${r.nspname.replace(/"/g, '""')}"`).join(', ');
      if (schemas) await client.query(`SET LOCAL search_path TO ${schemas}`);
      const res = await client.query({ text: sql, rowMode: 'array' });
      await client.query('COMMIT');
      const rows = res.rows as unknown[][];
      const truncated = rows.length >= rowLimit;
      return {
        columns: res.fields.map((f: FieldDef) => f.name),
        rows: rows.slice(0, rowLimit),
        rowCount: rows.length,
        durationMs: Math.round(performance.now() - start),
        truncated,
      };
    } finally {
      client.release();
    }
  }

  async close(): Promise<void> {
    await this.pool.end();
  }
}
