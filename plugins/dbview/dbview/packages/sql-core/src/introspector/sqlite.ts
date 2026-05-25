import Database from 'better-sqlite3';
import {
  IntrospectionError,
  type Column,
  type FKEdge,
  type SchemaGraph,
  type TableNode,
} from '@dbview/shared';
import type { SchemaIntrospector } from './types.js';

interface PragmaTableInfoRow {
  cid: number;
  name: string;
  type: string;
  notnull: 0 | 1;
  dflt_value: string | null;
  pk: number;
}

interface PragmaFkRow {
  id: number;
  seq: number;
  table: string;
  from: string;
  to: string;
  on_update: string;
  on_delete: string;
  match: string;
}

interface PragmaIndexListRow {
  seq: number;
  name: string;
  unique: 0 | 1;
  origin: string;
  partial: 0 | 1;
}

interface PragmaIndexInfoRow {
  seqno: number;
  cid: number;
  name: string;
}

const SCHEMA_NAME = 'main';

export class SqliteIntrospector implements SchemaIntrospector {
  private readonly db: Database.Database;

  constructor(filePath: string) {
    this.db = new Database(filePath, { readonly: true, fileMustExist: true });
    this.db.pragma('query_only = ON');
  }

  async introspect(): Promise<SchemaGraph> {
    try {
      const tables = this.db
        .prepare(
          `SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name`
        )
        .all() as Array<{ name: string }>;

      const tableNodes: TableNode[] = [];
      const edges: FKEdge[] = [];

      for (const { name } of tables) {
        const colsRaw = this.db
          .prepare(`PRAGMA table_info(${quoteIdent(name)})`)
          .all() as PragmaTableInfoRow[];
        const fks = this.db
          .prepare(`PRAGMA foreign_key_list(${quoteIdent(name)})`)
          .all() as PragmaFkRow[];
        const indexes = this.db
          .prepare(`PRAGMA index_list(${quoteIdent(name)})`)
          .all() as PragmaIndexListRow[];

        const uniqueCols = new Set<string>();
        for (const idx of indexes) {
          if (idx.unique === 1) {
            const cols = this.db
              .prepare(`PRAGMA index_info(${quoteIdent(idx.name)})`)
              .all() as PragmaIndexInfoRow[];
            if (cols.length === 1 && cols[0]) uniqueCols.add(cols[0].name);
          }
        }

        const fkCols = new Set(fks.map((f) => f.from));

        const columns: Column[] = colsRaw.map((c) => ({
          name: c.name,
          dataType: c.type || 'TEXT',
          nullable: c.notnull === 0,
          isPrimaryKey: c.pk > 0,
          isForeignKey: fkCols.has(c.name),
          isUnique: uniqueCols.has(c.name),
          defaultValue: c.dflt_value,
        }));

        tableNodes.push({
          id: `${SCHEMA_NAME}.${name}`,
          schema: SCHEMA_NAME,
          name,
          columns,
        });

        fks.forEach((fk, idx) => {
          edges.push({
            id: `${name}_fk_${fk.id}_${idx}`,
            source: `${SCHEMA_NAME}.${name}`,
            sourceColumn: fk.from,
            target: `${SCHEMA_NAME}.${fk.table}`,
            targetColumn: fk.to,
            onDelete: fk.on_delete,
            onUpdate: fk.on_update,
          });
        });
      }

      return {
        kind: 'relational',
        dialect: 'sqlite',
        tables: tableNodes,
        edges,
        generatedAt: new Date().toISOString(),
      };
    } catch (err) {
      throw new IntrospectionError(`SQLite introspection failed: ${(err as Error).message}`);
    }
  }

  async close(): Promise<void> {
    this.db.close();
  }
}

function quoteIdent(name: string): string {
  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name)) {
    throw new IntrospectionError(`Refusing unsafe identifier: ${name}`);
  }
  return `"${name}"`;
}
