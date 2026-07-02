import pg from 'pg';
import type { Pool as PgPool, PoolClient } from 'pg';
const { Pool } = pg;
import {
  IntrospectionError,
  type Column,
  type FKEdge,
  type SchemaGraph,
  type TableNode,
} from '@dbview/shared';
import type { SchemaIntrospector } from './types.js';

type PostgresWireDialect = 'postgres' | 'cockroach';

const COLUMNS_QUERY = `
SELECT
  c.table_schema,
  c.table_name,
  c.column_name,
  c.data_type,
  c.is_nullable,
  c.column_default,
  COALESCE(pk.is_pk, false) AS is_pk,
  COALESCE(uq.is_unique, false) AS is_unique
FROM information_schema.columns c
LEFT JOIN (
  SELECT kcu.table_schema, kcu.table_name, kcu.column_name, true AS is_pk
  FROM information_schema.table_constraints tc
  JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
   AND tc.table_schema = kcu.table_schema
  WHERE tc.constraint_type = 'PRIMARY KEY'
) pk
  ON pk.table_schema = c.table_schema
 AND pk.table_name = c.table_name
 AND pk.column_name = c.column_name
LEFT JOIN (
  SELECT kcu.table_schema, kcu.table_name, kcu.column_name, true AS is_unique
  FROM information_schema.table_constraints tc
  JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
   AND tc.table_schema = kcu.table_schema
  WHERE tc.constraint_type = 'UNIQUE'
) uq
  ON uq.table_schema = c.table_schema
 AND uq.table_name = c.table_name
 AND uq.column_name = c.column_name
WHERE c.table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY c.table_schema, c.table_name, c.ordinal_position;
`;

const FK_QUERY = `
SELECT
  con.conname AS constraint_name,
  src_ns.nspname AS src_schema,
  src_tbl.relname AS src_table,
  src_col.attname AS src_column,
  tgt_ns.nspname AS tgt_schema,
  tgt_tbl.relname AS tgt_table,
  tgt_col.attname AS tgt_column,
  con.confdeltype AS on_delete,
  con.confupdtype AS on_update
FROM pg_constraint con
JOIN pg_class src_tbl ON src_tbl.oid = con.conrelid
JOIN pg_namespace src_ns ON src_ns.oid = src_tbl.relnamespace
JOIN pg_class tgt_tbl ON tgt_tbl.oid = con.confrelid
JOIN pg_namespace tgt_ns ON tgt_ns.oid = tgt_tbl.relnamespace
JOIN unnest(con.conkey) WITH ORDINALITY AS sk(attnum, ord) ON true
JOIN unnest(con.confkey) WITH ORDINALITY AS tk(attnum, ord) ON sk.ord = tk.ord
JOIN pg_attribute src_col ON src_col.attrelid = con.conrelid AND src_col.attnum = sk.attnum
JOIN pg_attribute tgt_col ON tgt_col.attrelid = con.confrelid AND tgt_col.attnum = tk.attnum
WHERE con.contype = 'f'
  AND src_ns.nspname NOT IN ('pg_catalog', 'information_schema');
`;

export class PostgresIntrospector implements SchemaIntrospector {
  private readonly pool: PgPool;
  private readonly dialect: PostgresWireDialect;

  constructor(connectionString: string, dialect: PostgresWireDialect = 'postgres') {
    this.dialect = dialect;
    this.pool = new Pool({
      connectionString,
      max: 2,
      statement_timeout: 5_000,
      application_name: 'dbview-introspector',
    });
  }

  async introspect(): Promise<SchemaGraph> {
    let client: PoolClient | undefined;
    try {
      client = await this.pool.connect();
      await client.query('BEGIN READ ONLY');
      const [colsRes, fksRes] = await Promise.all([
        client.query(COLUMNS_QUERY),
        client.query(FK_QUERY),
      ]);
      await client.query('COMMIT');

      const tableMap = new Map<string, TableNode>();
      const fkColumnSet = new Set<string>();

      for (const row of fksRes.rows as Array<{
        src_schema: string;
        src_table: string;
        src_column: string;
      }>) {
        fkColumnSet.add(`${row.src_schema}.${row.src_table}.${row.src_column}`);
      }

      for (const row of colsRes.rows as Array<{
        table_schema: string;
        table_name: string;
        column_name: string;
        data_type: string;
        is_nullable: 'YES' | 'NO';
        column_default: string | null;
        is_pk: boolean;
        is_unique: boolean;
      }>) {
        const id = `${row.table_schema}.${row.table_name}`;
        let table = tableMap.get(id);
        if (!table) {
          table = {
            id,
            schema: row.table_schema,
            name: row.table_name,
            columns: [],
          };
          tableMap.set(id, table);
        }
        const col: Column = {
          name: row.column_name,
          dataType: row.data_type,
          nullable: row.is_nullable === 'YES',
          isPrimaryKey: row.is_pk,
          isForeignKey: fkColumnSet.has(`${row.table_schema}.${row.table_name}.${row.column_name}`),
          isUnique: row.is_unique,
          defaultValue: row.column_default,
        };
        table.columns.push(col);
      }

      const edges: FKEdge[] = (
        fksRes.rows as Array<{
          constraint_name: string;
          src_schema: string;
          src_table: string;
          src_column: string;
          tgt_schema: string;
          tgt_table: string;
          tgt_column: string;
          on_delete: string;
          on_update: string;
        }>
      ).map((r, idx) => ({
        id: `${r.constraint_name}_${idx}`,
        constraintName: r.constraint_name,
        source: `${r.src_schema}.${r.src_table}`,
        sourceColumn: r.src_column,
        target: `${r.tgt_schema}.${r.tgt_table}`,
        targetColumn: r.tgt_column,
        onDelete: r.on_delete,
        onUpdate: r.on_update,
      }));

      return {
        kind: 'relational',
        dialect: this.dialect,
        tables: [...tableMap.values()],
        edges,
        generatedAt: new Date().toISOString(),
      };
    } catch (err) {
      throw new IntrospectionError(
        `${this.dialect === 'cockroach' ? 'CockroachDB' : 'Postgres'} introspection failed: ${formatErr(err)}`
      );
    } finally {
      client?.release();
    }
  }

  async close(): Promise<void> {
    await this.pool.end();
  }
}

function formatErr(err: unknown): string {
  if (err instanceof AggregateError) {
    const inner = err.errors
      .map((e) => (e as { message?: string; code?: string }).message ?? String(e))
      .filter(Boolean);
    const code = (err as { code?: string }).code;
    return [code, inner.join('; ')].filter(Boolean).join(': ') || 'aggregate error';
  }
  const e = err as { message?: string; code?: string };
  return e.code && e.message ? `${e.code}: ${e.message}` : (e.message ?? String(err));
}
