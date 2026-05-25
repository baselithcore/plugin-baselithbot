import mysqlPkg from 'mysql2/promise';
import {
  IntrospectionError,
  type Column,
  type FKEdge,
  type SchemaGraph,
  type SqlDialect,
  type TableNode,
} from '@dbview/shared';
import type { SchemaIntrospector } from './types.js';

const { createPool } = mysqlPkg;

const COLUMNS_QUERY = `
SELECT
  c.TABLE_SCHEMA AS table_schema,
  c.TABLE_NAME   AS table_name,
  c.COLUMN_NAME  AS column_name,
  c.DATA_TYPE    AS data_type,
  c.IS_NULLABLE  AS is_nullable,
  c.COLUMN_DEFAULT AS column_default,
  CASE WHEN c.COLUMN_KEY = 'PRI' THEN 1 ELSE 0 END AS is_pk,
  CASE WHEN c.COLUMN_KEY = 'UNI' THEN 1 ELSE 0 END AS is_unique
FROM information_schema.COLUMNS c
WHERE c.TABLE_SCHEMA = DATABASE()
ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION
`;

const FK_QUERY = `
SELECT
  kcu.CONSTRAINT_NAME AS constraint_name,
  kcu.TABLE_SCHEMA    AS src_schema,
  kcu.TABLE_NAME      AS src_table,
  kcu.COLUMN_NAME     AS src_column,
  kcu.REFERENCED_TABLE_SCHEMA AS tgt_schema,
  kcu.REFERENCED_TABLE_NAME   AS tgt_table,
  kcu.REFERENCED_COLUMN_NAME  AS tgt_column,
  rc.DELETE_RULE      AS on_delete,
  rc.UPDATE_RULE      AS on_update
FROM information_schema.KEY_COLUMN_USAGE kcu
JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
  ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
 AND rc.CONSTRAINT_NAME   = kcu.CONSTRAINT_NAME
WHERE kcu.TABLE_SCHEMA = DATABASE()
  AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
`;

export class MysqlIntrospector implements SchemaIntrospector {
  private readonly pool: ReturnType<typeof createPool>;

  constructor(
    connectionString: string,
    private readonly dialect: SqlDialect = 'mysql',
  ) {
    this.pool = createPool({
      uri: connectionString,
      connectionLimit: 2,
      waitForConnections: true,
      multipleStatements: false,
    });
  }

  async introspect(): Promise<SchemaGraph> {
    let conn: Awaited<ReturnType<typeof this.pool.getConnection>> | undefined;
    try {
      conn = await this.pool.getConnection();
      const [colsRows] = await conn.query(COLUMNS_QUERY);
      const [fkRows] = await conn.query(FK_QUERY);

      const tableMap = new Map<string, TableNode>();
      const fkColumnSet = new Set<string>();

      for (const r of fkRows as Array<{
        src_schema: string;
        src_table: string;
        src_column: string;
      }>) {
        fkColumnSet.add(`${r.src_schema}.${r.src_table}.${r.src_column}`);
      }

      for (const row of colsRows as Array<{
        table_schema: string;
        table_name: string;
        column_name: string;
        data_type: string;
        is_nullable: 'YES' | 'NO';
        column_default: string | null;
        is_pk: 0 | 1;
        is_unique: 0 | 1;
      }>) {
        const id = `${row.table_schema}.${row.table_name}`;
        let table = tableMap.get(id);
        if (!table) {
          table = { id, schema: row.table_schema, name: row.table_name, columns: [] };
          tableMap.set(id, table);
        }
        const col: Column = {
          name: row.column_name,
          dataType: row.data_type,
          nullable: row.is_nullable === 'YES',
          isPrimaryKey: row.is_pk === 1,
          isForeignKey: fkColumnSet.has(`${row.table_schema}.${row.table_name}.${row.column_name}`),
          isUnique: row.is_unique === 1,
          defaultValue: row.column_default,
        };
        table.columns.push(col);
      }

      const edges: FKEdge[] = (
        fkRows as Array<{
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
      throw new IntrospectionError(`${this.dialect} introspection failed: ${formatErr(err)}`);
    } finally {
      conn?.release();
    }
  }

  async close(): Promise<void> {
    await this.pool.end();
  }
}

function formatErr(err: unknown): string {
  if (err instanceof AggregateError) {
    const inner = err.errors
      .map((e) => (e as { message?: string }).message ?? String(e))
      .filter(Boolean);
    const code = (err as { code?: string }).code;
    return [code, inner.join('; ')].filter(Boolean).join(': ') || 'aggregate error';
  }
  const e = err as { message?: string; code?: string };
  return e.code && e.message ? `${e.code}: ${e.message}` : (e.message ?? String(err));
}
