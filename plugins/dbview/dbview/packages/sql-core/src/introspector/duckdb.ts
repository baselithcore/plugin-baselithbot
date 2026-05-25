import { DuckDBInstance, type DuckDBConnection } from '@duckdb/node-api';
import {
  IntrospectionError,
  type Column,
  type FKEdge,
  type SchemaGraph,
  type TableNode,
} from '@dbview/shared';
import type { SchemaIntrospector } from './types.js';

const COLUMNS_QUERY = `
SELECT
  table_schema,
  table_name,
  column_name,
  data_type,
  is_nullable,
  column_default
FROM information_schema.columns
WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'main_information_schema')
ORDER BY table_schema, table_name, ordinal_position
`;

const PK_QUERY = `
SELECT
  table_schema,
  table_name,
  column_name
FROM information_schema.key_column_usage kcu
JOIN information_schema.table_constraints tc
  USING (constraint_schema, constraint_name, table_schema, table_name)
WHERE tc.constraint_type = 'PRIMARY KEY'
`;

const FK_QUERY = `
SELECT
  tc.constraint_name AS constraint_name,
  kcu.table_schema   AS src_schema,
  kcu.table_name     AS src_table,
  kcu.column_name    AS src_column,
  ccu.table_schema   AS tgt_schema,
  ccu.table_name     AS tgt_table,
  ccu.column_name    AS tgt_column
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  USING (constraint_schema, constraint_name)
JOIN information_schema.constraint_column_usage ccu
  USING (constraint_schema, constraint_name)
WHERE tc.constraint_type = 'FOREIGN KEY'
`;

export class DuckdbIntrospector implements SchemaIntrospector {
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

  async introspect(): Promise<SchemaGraph> {
    try {
      const conn = await this.getConnection();
      const [colsR, pksR, fksR] = await Promise.all([
        conn.runAndReadAll(COLUMNS_QUERY),
        conn.runAndReadAll(PK_QUERY),
        conn.runAndReadAll(FK_QUERY).catch(() => null),
      ]);
      const colsRows = colsR.getRowObjectsJS() as Array<{
        table_schema: string;
        table_name: string;
        column_name: string;
        data_type: string;
        is_nullable: string | boolean;
        column_default: string | null;
      }>;
      const pkRows = pksR.getRowObjectsJS() as Array<{
        table_schema: string;
        table_name: string;
        column_name: string;
      }>;
      const pkSet = new Set<string>();
      for (const r of pkRows) {
        pkSet.add(`${r.table_schema}.${r.table_name}.${r.column_name}`);
      }

      const fkRows = (fksR?.getRowObjectsJS() ?? []) as Array<{
        constraint_name: string;
        src_schema: string;
        src_table: string;
        src_column: string;
        tgt_schema: string;
        tgt_table: string;
        tgt_column: string;
      }>;
      const fkColumnSet = new Set<string>();
      for (const r of fkRows) {
        fkColumnSet.add(`${r.src_schema}.${r.src_table}.${r.src_column}`);
      }

      const tableMap = new Map<string, TableNode>();
      for (const row of colsRows) {
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
        const colKey = `${row.table_schema}.${row.table_name}.${row.column_name}`;
        const nullable =
          row.is_nullable === true ||
          String(row.is_nullable).toUpperCase() === 'YES' ||
          String(row.is_nullable).toUpperCase() === 'TRUE';
        const col: Column = {
          name: row.column_name,
          dataType: row.data_type,
          nullable,
          isPrimaryKey: pkSet.has(colKey),
          isForeignKey: fkColumnSet.has(colKey),
          isUnique: false,
          defaultValue: row.column_default,
        };
        table.columns.push(col);
      }

      const edges: FKEdge[] = fkRows.map((r, idx) => ({
        id: `${r.constraint_name}_${idx}`,
        constraintName: r.constraint_name,
        source: `${r.src_schema}.${r.src_table}`,
        sourceColumn: r.src_column,
        target: `${r.tgt_schema}.${r.tgt_table}`,
        targetColumn: r.tgt_column,
      }));

      return {
        kind: 'relational',
        dialect: 'duckdb',
        tables: [...tableMap.values()],
        edges,
        generatedAt: new Date().toISOString(),
      };
    } catch (err) {
      throw new IntrospectionError(
        `DuckDB introspection failed: ${(err as Error).message ?? String(err)}`,
      );
    }
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
