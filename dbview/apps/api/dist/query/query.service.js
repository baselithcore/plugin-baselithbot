var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
import { Injectable, NotFoundException } from '@nestjs/common';
import { isDocumentDialect, isGraphDialect, isKeyValueDialect, isSaasDialect, isSearchDialect, isSqlDialect, isVectorDialect, } from '@dbview/shared';
import { SqlSafetyValidator, buildKnownSetsMemoized } from '@dbview/sql-core';
import { CypherSafetyValidator } from '@dbview/cypher-core';
import { SalesforceSafetyValidator } from '../engine/salesforce/safety.js';
import { SalesforceDataCloudSafetyValidator } from '../engine/salesforce-data-cloud/safety.js';
import { ConnectionsService } from '../connections/connections.service.js';
import { SchemaService } from '../schema/schema.service.js';
import { createQueryEngine } from '../engine/factory.js';
import { EnginePool } from '../engine/engine-pool.js';
import { queryExecutionLatency, queryExecutions } from '../observability/metrics.registry.js';
const IDENT_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;
let QueryService = class QueryService {
    connections;
    schema;
    enginePool;
    sqlValidator = new SqlSafetyValidator();
    cypherValidator = new CypherSafetyValidator();
    soqlValidator = new SalesforceSafetyValidator();
    sdcValidator = new SalesforceDataCloudSafetyValidator();
    constructor(connections, schema, enginePool) {
        this.connections = connections;
        this.schema = schema;
        this.enginePool = enginePool;
    }
    /**
     * Run a function with a query engine, preferring a pooled instance when the
     * dialect supports it. Non-pooled engines are closed after use; pooled ones
     * stay open and are managed by `EnginePool`.
     */
    async withEngine(dialect, connectionString, fn) {
        const pooled = this.enginePool.acquire(dialect, connectionString);
        const engine = pooled ?? createQueryEngine(dialect, connectionString);
        try {
            return await fn(engine);
        }
        finally {
            if (!pooled)
                await engine.close();
        }
    }
    async sample(req, principal) {
        const { dialect, connectionString } = this.connections.resolvePlain(req.connectionId, principal);
        const graph = await this.schema.getGraph(req.connectionId, principal);
        if (graph.kind === 'relational' && isSqlDialect(dialect)) {
            const table = graph.tables.find((t) => t.id === req.tableId);
            if (!table)
                throw new NotFoundException(`Table '${req.tableId}' not found in schema.`);
            if (!IDENT_RE.test(table.schema) || !IDENT_RE.test(table.name)) {
                throw new NotFoundException(`Refusing unsafe table identifier.`);
            }
            const cols = table.columns
                .filter((c) => IDENT_RE.test(c.name))
                .map((c) => quoteIdent(c.name, dialect));
            if (cols.length === 0) {
                throw new NotFoundException('No safely-named columns to sample.');
            }
            const qualifies = dialect === 'postgres' || dialect === 'mssql' || dialect === 'oracle';
            const ref = qualifies
                ? `${quoteIdent(table.schema, dialect)}.${quoteIdent(table.name, dialect)}`
                : quoteIdent(table.name, dialect);
            // Row-limit clause is dialect-specific: T-SQL puts the count between
            // SELECT and the column list, Oracle accepts only `FETCH FIRST … ROWS
            // ONLY` (no `LIMIT`), everyone else uses the standard `LIMIT n` suffix.
            const sql = dialect === 'mssql'
                ? `SELECT TOP ${req.rowLimit} ${cols.join(', ')} FROM ${ref}`
                : dialect === 'oracle'
                    ? `SELECT ${cols.join(', ')} FROM ${ref} FETCH FIRST ${req.rowLimit} ROWS ONLY`
                    : `SELECT ${cols.join(', ')} FROM ${ref} LIMIT ${req.rowLimit}`;
            return this.withEngine(dialect, connectionString, (e) => e.execute(sql, req.rowLimit));
        }
        if (graph.kind === 'relational' && isSaasDialect(dialect)) {
            const table = graph.tables.find((t) => t.id === req.tableId);
            if (!table)
                throw new NotFoundException(`SObject '${req.tableId}' not found in schema.`);
            if (!IDENT_RE.test(table.name)) {
                throw new NotFoundException('Refusing unsafe sObject identifier.');
            }
            const cols = table.columns.filter((c) => IDENT_RE.test(c.name)).map((c) => c.name);
            if (cols.length === 0) {
                throw new NotFoundException('No safely-named fields to sample.');
            }
            const query = dialect === 'salesforce-data-cloud'
                ? `SELECT ${cols.map((c) => `"${c}"`).join(', ')} FROM "${table.name}" LIMIT ${req.rowLimit}`
                : `SELECT ${cols.join(', ')} FROM ${table.name} LIMIT ${req.rowLimit}`;
            return this.withEngine(dialect, connectionString, (e) => e.execute(query, req.rowLimit));
        }
        if (graph.kind === 'graph' && isGraphDialect(dialect)) {
            const label = graph.labels.find((l) => l.id === req.tableId);
            if (!label)
                throw new NotFoundException(`Label '${req.tableId}' not found.`);
            if (!IDENT_RE.test(label.label)) {
                throw new NotFoundException('Refusing unsafe label identifier.');
            }
            const cypher = `MATCH (n:\`${label.label}\`) RETURN n LIMIT ${req.rowLimit}`;
            return this.withEngine(dialect, connectionString, (e) => e.execute(cypher, req.rowLimit));
        }
        if (graph.kind === 'vector' && isVectorDialect(dialect)) {
            const collection = graph.collections.find((c) => c.id === req.tableId);
            if (!collection) {
                throw new NotFoundException(`Collection '${req.tableId}' not found.`);
            }
            const envelope = JSON.stringify({
                op: 'scroll',
                collection: collection.name,
                limit: req.rowLimit,
            });
            return this.withEngine(dialect, connectionString, (e) => e.execute(envelope, req.rowLimit));
        }
        if (graph.kind === 'keyvalue' && isKeyValueDialect(dialect)) {
            const ns = graph.namespaces.find((n) => n.pattern === req.tableId);
            if (!ns)
                throw new NotFoundException(`Namespace '${req.tableId}' not found.`);
            const pattern = ns.pattern === '(no-prefix)' ? '*' : ns.pattern;
            const cmd = `SCAN 0 MATCH ${pattern} COUNT ${req.rowLimit}`;
            return this.withEngine(dialect, connectionString, (e) => e.execute(cmd, req.rowLimit));
        }
        if (graph.kind === 'search' && isSearchDialect(dialect)) {
            const idx = graph.indices.find((i) => i.id === req.tableId);
            if (!idx)
                throw new NotFoundException(`Index '${req.tableId}' not found.`);
            const envelope = JSON.stringify({
                op: 'search',
                index: idx.name,
                body: { query: { match_all: {} }, size: req.rowLimit },
            });
            return this.withEngine(dialect, connectionString, (e) => e.execute(envelope, req.rowLimit));
        }
        if (graph.kind === 'document' && isDocumentDialect(dialect)) {
            const coll = graph.collections.find((c) => c.id === req.tableId);
            if (!coll)
                throw new NotFoundException(`Collection '${req.tableId}' not found.`);
            const envelope = JSON.stringify({
                op: 'find',
                collection: coll.name,
                limit: req.rowLimit,
            });
            return this.withEngine(dialect, connectionString, (e) => e.execute(envelope, req.rowLimit));
        }
        throw new Error('Unsupported dialect for sample.');
    }
    async execute(req, principal) {
        const { dialect, connectionString } = this.connections.resolvePlain(req.connectionId, principal);
        const graph = await this.schema.getGraph(req.connectionId, principal);
        let sanitizedQuery;
        if (graph.kind === 'relational' && isSqlDialect(dialect)) {
            const { knownTables, knownColumns } = buildKnownSetsMemoized(graph);
            const r = this.sqlValidator.validate(req.query, {
                dialect,
                allowDml: false,
                rowLimit: req.rowLimit,
                knownTables,
                knownColumns,
            });
            sanitizedQuery = r.sql;
        }
        else if (graph.kind === 'relational' && isSaasDialect(dialect)) {
            if (dialect === 'salesforce-data-cloud') {
                const { knownTables, knownColumns } = buildKnownSetsMemoized(graph);
                // Salesforce Data Cloud SQL has no schema namespace; strip any
                // `data_cloud.` prefix the caller may have copied from the schema
                // graph IDs. The known-tables set contains both prefixed and bare
                // forms, so this rewrite is safe.
                const stripped = stripDataCloudSchemaPrefix(req.query);
                const r = this.sdcValidator.validate(stripped, {
                    rowLimit: req.rowLimit,
                    knownTables,
                    knownColumns,
                });
                sanitizedQuery = r.sql;
            }
            else {
                const knownSObjects = new Set(graph.tables.map((t) => t.name.toLowerCase()));
                const knownFields = new Map();
                for (const t of graph.tables) {
                    knownFields.set(t.name.toLowerCase(), new Set(t.columns.map((c) => c.name.toLowerCase())));
                }
                const r = this.soqlValidator.validate(req.query, {
                    rowLimit: req.rowLimit,
                    knownSObjects,
                    knownFields,
                });
                sanitizedQuery = r.query;
            }
        }
        else if (graph.kind === 'graph' && isGraphDialect(dialect)) {
            const r = this.cypherValidator.validate(req.query, {
                schema: graph,
                rowLimit: req.rowLimit,
                allowWrites: false,
            });
            sanitizedQuery = r.query;
        }
        else if (graph.kind === 'vector' && isVectorDialect(dialect)) {
            // Qdrant queries are JSON envelopes; the executor parses + enforces read-only.
            sanitizedQuery = req.query;
        }
        else if (graph.kind === 'keyvalue' && isKeyValueDialect(dialect)) {
            // Redis commands; the executor validates against read-only whitelist.
            sanitizedQuery = req.query;
        }
        else if (graph.kind === 'search' && isSearchDialect(dialect)) {
            // Elasticsearch JSON envelopes; the executor validates op + body keys.
            sanitizedQuery = req.query;
        }
        else if (graph.kind === 'document' && isDocumentDialect(dialect)) {
            // MongoDB JSON envelopes; the executor validates op + pipeline.
            sanitizedQuery = req.query;
        }
        else {
            throw new Error(`Schema kind '${graph.kind}' incompatible with dialect '${dialect}'.`);
        }
        const start = process.hrtime.bigint();
        try {
            const res = await this.withEngine(dialect, connectionString, (e) => e.execute(sanitizedQuery, req.rowLimit));
            const seconds = Number(process.hrtime.bigint() - start) / 1e9;
            queryExecutionLatency.labels({ dialect }).observe(seconds);
            queryExecutions.labels({ dialect, status: 'ok' }).inc();
            return res;
        }
        catch (err) {
            const seconds = Number(process.hrtime.bigint() - start) / 1e9;
            queryExecutionLatency.labels({ dialect }).observe(seconds);
            queryExecutions.labels({ dialect, status: 'error' }).inc();
            throw err;
        }
    }
};
QueryService = __decorate([
    Injectable(),
    __metadata("design:paramtypes", [ConnectionsService,
        SchemaService,
        EnginePool])
], QueryService);
export { QueryService };
/**
 * Strip `data_cloud.` qualifier from table references. The introspector tags
 * every SDC entity with the synthetic schema `data_cloud` for internal graph
 * uniqueness, but Salesforce Data Cloud SQL rejects schema-qualified names
 * (`DataSourceEntity ... not found`). Removing the prefix is a no-op when the
 * caller already used bare names.
 */
function stripDataCloudSchemaPrefix(sql) {
    return sql.replace(/\bdata_cloud\.(?=["A-Za-z_])/g, '');
}
function quoteIdent(name, dialect) {
    if (!IDENT_RE.test(name))
        throw new Error(`Unsafe identifier: ${name}`);
    switch (dialect) {
        case 'postgres':
        case 'sqlite':
        case 'cockroach':
        case 'oracle':
        case 'duckdb':
            return `"${name}"`;
        case 'mysql':
        case 'mariadb':
        case 'clickhouse':
            return `\`${name}\``;
        case 'mssql':
            return `[${name}]`;
    }
}
//# sourceMappingURL=query.service.js.map