import Database from 'better-sqlite3';
import { IntrospectionError, } from '@dbview/shared';
const SCHEMA_NAME = 'main';
export class SqliteIntrospector {
    db;
    constructor(filePath) {
        this.db = new Database(filePath, { readonly: true, fileMustExist: true });
        this.db.pragma('query_only = ON');
    }
    async introspect() {
        try {
            const tables = this.db
                .prepare(`SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name`)
                .all();
            const tableNodes = [];
            const edges = [];
            for (const { name } of tables) {
                const colsRaw = this.db
                    .prepare(`PRAGMA table_info(${quoteIdent(name)})`)
                    .all();
                const fks = this.db
                    .prepare(`PRAGMA foreign_key_list(${quoteIdent(name)})`)
                    .all();
                const indexes = this.db
                    .prepare(`PRAGMA index_list(${quoteIdent(name)})`)
                    .all();
                const uniqueCols = new Set();
                for (const idx of indexes) {
                    if (idx.unique === 1) {
                        const cols = this.db
                            .prepare(`PRAGMA index_info(${quoteIdent(idx.name)})`)
                            .all();
                        if (cols.length === 1 && cols[0])
                            uniqueCols.add(cols[0].name);
                    }
                }
                const fkCols = new Set(fks.map((f) => f.from));
                const columns = colsRaw.map((c) => ({
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
        }
        catch (err) {
            throw new IntrospectionError(`SQLite introspection failed: ${err.message}`);
        }
    }
    async close() {
        this.db.close();
    }
}
function quoteIdent(name) {
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name)) {
        throw new IntrospectionError(`Refusing unsafe identifier: ${name}`);
    }
    return `"${name}"`;
}
//# sourceMappingURL=sqlite.js.map