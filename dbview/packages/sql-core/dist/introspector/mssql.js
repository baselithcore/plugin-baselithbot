import mssql from 'mssql';
import { IntrospectionError, } from '@dbview/shared';
const COLUMNS_QUERY = `
SELECT
  s.name  AS table_schema,
  t.name  AS table_name,
  c.name  AS column_name,
  TYPE_NAME(c.user_type_id) AS data_type,
  c.is_nullable AS is_nullable,
  CAST(dc.definition AS NVARCHAR(MAX)) AS column_default,
  CASE WHEN pk.column_id IS NOT NULL THEN 1 ELSE 0 END AS is_pk,
  CASE WHEN uq.column_id IS NOT NULL THEN 1 ELSE 0 END AS is_unique
FROM sys.columns c
JOIN sys.tables  t  ON t.object_id = c.object_id
JOIN sys.schemas s  ON s.schema_id = t.schema_id
LEFT JOIN sys.default_constraints dc ON dc.object_id = c.default_object_id
LEFT JOIN (
  SELECT ic.object_id, ic.column_id
  FROM sys.indexes i
  JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
  WHERE i.is_primary_key = 1
) pk ON pk.object_id = c.object_id AND pk.column_id = c.column_id
LEFT JOIN (
  SELECT ic.object_id, ic.column_id
  FROM sys.indexes i
  JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
  WHERE i.is_unique_constraint = 1
) uq ON uq.object_id = c.object_id AND uq.column_id = c.column_id
WHERE s.name NOT IN ('sys','INFORMATION_SCHEMA')
ORDER BY s.name, t.name, c.column_id
`;
const FK_QUERY = `
SELECT
  fk.name AS constraint_name,
  sps.name AS src_schema,
  spt.name AS src_table,
  spc.name AS src_column,
  rps.name AS tgt_schema,
  rpt.name AS tgt_table,
  rpc.name AS tgt_column,
  fk.delete_referential_action_desc AS on_delete,
  fk.update_referential_action_desc AS on_update
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
JOIN sys.tables  spt ON spt.object_id = fkc.parent_object_id
JOIN sys.schemas sps ON sps.schema_id = spt.schema_id
JOIN sys.columns spc ON spc.object_id = fkc.parent_object_id AND spc.column_id = fkc.parent_column_id
JOIN sys.tables  rpt ON rpt.object_id = fkc.referenced_object_id
JOIN sys.schemas rps ON rps.schema_id = rpt.schema_id
JOIN sys.columns rpc ON rpc.object_id = fkc.referenced_object_id AND rpc.column_id = fkc.referenced_column_id
`;
export class MssqlIntrospector {
    poolPromise;
    constructor(connectionString) {
        const pool = new mssql.ConnectionPool(connectionString);
        this.poolPromise = pool.connect();
    }
    async introspect() {
        try {
            const pool = await this.poolPromise;
            const colsRes = await pool.request().query(COLUMNS_QUERY);
            const fksRes = await pool.request().query(FK_QUERY);
            const tableMap = new Map();
            const fkColumnSet = new Set();
            for (const r of fksRes.recordset) {
                fkColumnSet.add(`${r.src_schema}.${r.src_table}.${r.src_column}`);
            }
            for (const row of colsRes.recordset) {
                const id = `${row.table_schema}.${row.table_name}`;
                let table = tableMap.get(id);
                if (!table) {
                    table = { id, schema: row.table_schema, name: row.table_name, columns: [] };
                    tableMap.set(id, table);
                }
                const col = {
                    name: row.column_name,
                    dataType: row.data_type,
                    nullable: !!row.is_nullable,
                    isPrimaryKey: row.is_pk === 1,
                    isForeignKey: fkColumnSet.has(`${row.table_schema}.${row.table_name}.${row.column_name}`),
                    isUnique: row.is_unique === 1,
                    defaultValue: row.column_default,
                };
                table.columns.push(col);
            }
            const edges = fksRes.recordset.map((r, idx) => ({
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
                dialect: 'mssql',
                tables: [...tableMap.values()],
                edges,
                generatedAt: new Date().toISOString(),
            };
        }
        catch (err) {
            throw new IntrospectionError(`SQL Server introspection failed: ${formatErr(err)}`);
        }
    }
    async close() {
        const pool = await this.poolPromise;
        await pool.close();
    }
}
function formatErr(err) {
    if (err instanceof AggregateError) {
        const inner = err.errors
            .map((e) => e.message ?? String(e))
            .filter(Boolean);
        const code = err.code;
        return [code, inner.join('; ')].filter(Boolean).join(': ') || 'aggregate error';
    }
    const e = err;
    return e.code && e.message ? `${e.code}: ${e.message}` : (e.message ?? String(err));
}
//# sourceMappingURL=mssql.js.map