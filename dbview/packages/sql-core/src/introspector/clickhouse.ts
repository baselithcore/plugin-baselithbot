import { createClient, type ClickHouseClient } from '@clickhouse/client';
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
  database AS table_schema,
  table    AS table_name,
  name     AS column_name,
  type     AS data_type,
  is_in_primary_key AS is_pk,
  default_expression AS column_default
FROM system.columns
WHERE database NOT IN ('system', 'INFORMATION_SCHEMA', 'information_schema')
ORDER BY database, table, position
`;

export class ClickhouseIntrospector implements SchemaIntrospector {
  private client: ClickHouseClient | undefined;

  constructor(private readonly connectionString: string) {}

  private getClient(): ClickHouseClient {
    if (!this.client) {
      this.client = createClient({
        url: this.connectionString,
        request_timeout: 5_000,
        application: 'dbview-introspector',
        clickhouse_settings: { readonly: '1' },
      });
    }
    return this.client;
  }

  async introspect(): Promise<SchemaGraph> {
    try {
      const client = this.getClient();
      const rs = await client.query({ query: COLUMNS_QUERY, format: 'JSONEachRow' });
      const rows = (await rs.json()) as Array<{
        table_schema: string;
        table_name: string;
        column_name: string;
        data_type: string;
        is_pk: number | string | boolean;
        column_default: string | null;
      }>;

      const tableMap = new Map<string, TableNode>();
      for (const row of rows) {
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
        const isPk =
          row.is_pk === 1 ||
          row.is_pk === '1' ||
          row.is_pk === true ||
          String(row.is_pk).toLowerCase() === 'true';
        // ClickHouse Nullable(T) → strip wrapper to check nullability.
        const nullable = /^Nullable\(/i.test(row.data_type);
        const col: Column = {
          name: row.column_name,
          dataType: row.data_type,
          nullable,
          isPrimaryKey: isPk,
          isForeignKey: false,
          isUnique: false,
          defaultValue: row.column_default || null,
        };
        table.columns.push(col);
      }

      const edges: FKEdge[] = []; // ClickHouse has no FK constraints.
      return {
        kind: 'relational',
        dialect: 'clickhouse',
        tables: [...tableMap.values()],
        edges,
        generatedAt: new Date().toISOString(),
      };
    } catch (err) {
      throw new IntrospectionError(
        `ClickHouse introspection failed: ${(err as Error).message ?? String(err)}`
      );
    }
  }

  async close(): Promise<void> {
    if (this.client) {
      await this.client.close();
      this.client = undefined;
    }
  }
}
