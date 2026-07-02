import oracledb from 'oracledb';
import {
  IntrospectionError,
  type Column,
  type FKEdge,
  type SchemaGraph,
  type TableNode,
} from '@dbview/shared';
import type { SchemaIntrospector } from './types.js';
import { parseOracleUrl } from '../executor/oracle-url.js';

const SYSTEM_SCHEMAS = [
  'SYS',
  'SYSTEM',
  'XDB',
  'CTXSYS',
  'MDSYS',
  'WMSYS',
  'EXFSYS',
  'DBSNMP',
  'APPQOSSYS',
  'AUDSYS',
  'OUTLN',
  'ORDSYS',
  'ORDDATA',
  'ORDPLUGINS',
  'OLAPSYS',
  'LBACSYS',
  'DVSYS',
  'GSMADMIN_INTERNAL',
  'OJVMSYS',
  'DBSFWUSER',
  'GGSYS',
  'REMOTE_SCHEDULER_AGENT',
  'ANONYMOUS',
  'APEX_PUBLIC_USER',
  'FLOWS_FILES',
  'MDDATA',
  'ORACLE_OCM',
  'PUBLIC',
  'SI_INFORMTN_SCHEMA',
  'SPATIAL_CSW_ADMIN_USR',
  'SPATIAL_WFS_ADMIN_USR',
  'XS$NULL',
];

const COLUMNS_QUERY = `
SELECT
  c.OWNER         AS table_schema,
  c.TABLE_NAME    AS table_name,
  c.COLUMN_NAME   AS column_name,
  c.DATA_TYPE     AS data_type,
  c.NULLABLE      AS is_nullable,
  c.DATA_DEFAULT  AS column_default,
  CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END AS is_pk,
  CASE WHEN uq.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END AS is_unique
FROM ALL_TAB_COLUMNS c
LEFT JOIN (
  SELECT acc.OWNER, acc.TABLE_NAME, acc.COLUMN_NAME
  FROM ALL_CONSTRAINTS ac
  JOIN ALL_CONS_COLUMNS acc
    ON acc.OWNER = ac.OWNER
   AND acc.CONSTRAINT_NAME = ac.CONSTRAINT_NAME
  WHERE ac.CONSTRAINT_TYPE = 'P'
) pk
  ON pk.OWNER = c.OWNER
 AND pk.TABLE_NAME = c.TABLE_NAME
 AND pk.COLUMN_NAME = c.COLUMN_NAME
LEFT JOIN (
  SELECT acc.OWNER, acc.TABLE_NAME, acc.COLUMN_NAME
  FROM ALL_CONSTRAINTS ac
  JOIN ALL_CONS_COLUMNS acc
    ON acc.OWNER = ac.OWNER
   AND acc.CONSTRAINT_NAME = ac.CONSTRAINT_NAME
  WHERE ac.CONSTRAINT_TYPE = 'U'
) uq
  ON uq.OWNER = c.OWNER
 AND uq.TABLE_NAME = c.TABLE_NAME
 AND uq.COLUMN_NAME = c.COLUMN_NAME
WHERE c.OWNER NOT IN (__SYSTEM_SCHEMAS__)
ORDER BY c.OWNER, c.TABLE_NAME, c.COLUMN_ID
`;

const FK_QUERY = `
SELECT
  ac.CONSTRAINT_NAME AS constraint_name,
  ac.OWNER           AS src_schema,
  ac.TABLE_NAME      AS src_table,
  acc.COLUMN_NAME    AS src_column,
  pk_ac.OWNER        AS tgt_schema,
  pk_ac.TABLE_NAME   AS tgt_table,
  pk_acc.COLUMN_NAME AS tgt_column,
  ac.DELETE_RULE     AS on_delete
FROM ALL_CONSTRAINTS ac
JOIN ALL_CONS_COLUMNS acc
  ON acc.OWNER = ac.OWNER
 AND acc.CONSTRAINT_NAME = ac.CONSTRAINT_NAME
JOIN ALL_CONSTRAINTS pk_ac
  ON pk_ac.OWNER = ac.R_OWNER
 AND pk_ac.CONSTRAINT_NAME = ac.R_CONSTRAINT_NAME
JOIN ALL_CONS_COLUMNS pk_acc
  ON pk_acc.OWNER = pk_ac.OWNER
 AND pk_acc.CONSTRAINT_NAME = pk_ac.CONSTRAINT_NAME
 AND pk_acc.POSITION = acc.POSITION
WHERE ac.CONSTRAINT_TYPE = 'R'
  AND ac.OWNER NOT IN (__SYSTEM_SCHEMAS__)
`;

function bindSystemSchemas(sql: string): string {
  const list = SYSTEM_SCHEMAS.map((s) => `'${s}'`).join(', ');
  return sql.replace(/__SYSTEM_SCHEMAS__/g, list);
}

export class OracleIntrospector implements SchemaIntrospector {
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
        poolMax: 2,
        poolIncrement: 1,
      });
    }
    return this.pool;
  }

  async introspect(): Promise<SchemaGraph> {
    let conn: oracledb.Connection | undefined;
    try {
      const pool = await this.getPool();
      conn = await pool.getConnection();
      await conn.execute('SET TRANSACTION READ ONLY');
      const [colsRes, fksRes] = await Promise.all([
        conn.execute<{
          TABLE_SCHEMA: string;
          TABLE_NAME: string;
          COLUMN_NAME: string;
          DATA_TYPE: string;
          IS_NULLABLE: 'Y' | 'N';
          COLUMN_DEFAULT: string | null;
          IS_PK: number;
          IS_UNIQUE: number;
        }>(bindSystemSchemas(COLUMNS_QUERY), [], { outFormat: oracledb.OUT_FORMAT_OBJECT }),
        conn.execute<{
          CONSTRAINT_NAME: string;
          SRC_SCHEMA: string;
          SRC_TABLE: string;
          SRC_COLUMN: string;
          TGT_SCHEMA: string;
          TGT_TABLE: string;
          TGT_COLUMN: string;
          ON_DELETE: string;
        }>(bindSystemSchemas(FK_QUERY), [], { outFormat: oracledb.OUT_FORMAT_OBJECT }),
      ]);
      await conn.commit();

      const tableMap = new Map<string, TableNode>();
      const fkColumnSet = new Set<string>();
      for (const row of fksRes.rows ?? []) {
        fkColumnSet.add(`${row.SRC_SCHEMA}.${row.SRC_TABLE}.${row.SRC_COLUMN}`);
      }
      for (const row of colsRes.rows ?? []) {
        const id = `${row.TABLE_SCHEMA}.${row.TABLE_NAME}`;
        let table = tableMap.get(id);
        if (!table) {
          table = {
            id,
            schema: row.TABLE_SCHEMA,
            name: row.TABLE_NAME,
            columns: [],
          };
          tableMap.set(id, table);
        }
        const col: Column = {
          name: row.COLUMN_NAME,
          dataType: row.DATA_TYPE,
          nullable: row.IS_NULLABLE === 'Y',
          isPrimaryKey: row.IS_PK === 1,
          isForeignKey: fkColumnSet.has(`${row.TABLE_SCHEMA}.${row.TABLE_NAME}.${row.COLUMN_NAME}`),
          isUnique: row.IS_UNIQUE === 1,
          defaultValue: row.COLUMN_DEFAULT,
        };
        table.columns.push(col);
      }
      const edges: FKEdge[] = (fksRes.rows ?? []).map((r, idx) => ({
        id: `${r.CONSTRAINT_NAME}_${idx}`,
        constraintName: r.CONSTRAINT_NAME,
        source: `${r.SRC_SCHEMA}.${r.SRC_TABLE}`,
        sourceColumn: r.SRC_COLUMN,
        target: `${r.TGT_SCHEMA}.${r.TGT_TABLE}`,
        targetColumn: r.TGT_COLUMN,
        onDelete: r.ON_DELETE,
      }));
      return {
        kind: 'relational',
        dialect: 'oracle',
        tables: [...tableMap.values()],
        edges,
        generatedAt: new Date().toISOString(),
      };
    } catch (err) {
      throw new IntrospectionError(
        `Oracle introspection failed: ${(err as Error).message ?? String(err)}`
      );
    } finally {
      await conn?.close();
    }
  }

  async close(): Promise<void> {
    if (this.pool) {
      await this.pool.close(0);
      this.pool = undefined;
    }
  }
}
