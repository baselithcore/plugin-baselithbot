import { z } from 'zod';
export const SqlDialectSchema = z.enum([
    'postgres',
    'mysql',
    'mariadb',
    'mssql',
    'sqlite',
    'cockroach',
    'oracle',
    'clickhouse',
    'duckdb',
]);
export const GraphDialectSchema = z.enum(['neo4j', 'falkordb', 'ultipa']);
export const DocumentDialectSchema = z.enum(['mongodb']);
export const VectorDialectSchema = z.enum(['qdrant']);
export const KeyValueDialectSchema = z.enum(['redis']);
export const SearchDialectSchema = z.enum(['elasticsearch']);
export const SaasDialectSchema = z.enum(['salesforce', 'salesforce-data-cloud']);
export const DialectSchema = z.enum([
    'postgres',
    'mysql',
    'mariadb',
    'mssql',
    'sqlite',
    'cockroach',
    'oracle',
    'clickhouse',
    'duckdb',
    'mongodb',
    'neo4j',
    'falkordb',
    'ultipa',
    'qdrant',
    'redis',
    'elasticsearch',
    'salesforce',
    'salesforce-data-cloud',
]);
export const SUPPORTED_DIALECTS = [
    'postgres',
    'mysql',
    'mariadb',
    'mssql',
    'sqlite',
    'cockroach',
    'oracle',
    'clickhouse',
    'duckdb',
    'mongodb',
    'neo4j',
    'falkordb',
    'ultipa',
    'qdrant',
    'redis',
    'elasticsearch',
    'salesforce',
    'salesforce-data-cloud',
];
const SQL_DIALECTS = new Set([
    'postgres',
    'mysql',
    'mariadb',
    'mssql',
    'sqlite',
    'cockroach',
    'oracle',
    'clickhouse',
    'duckdb',
]);
const GRAPH_DIALECTS = new Set(['neo4j', 'falkordb', 'ultipa']);
const DOCUMENT_DIALECTS = new Set(['mongodb']);
const VECTOR_DIALECTS = new Set(['qdrant']);
const KEYVALUE_DIALECTS = new Set(['redis']);
const SEARCH_DIALECTS = new Set(['elasticsearch']);
const SAAS_DIALECTS = new Set(['salesforce', 'salesforce-data-cloud']);
export function dialectKind(d) {
    if (GRAPH_DIALECTS.has(d))
        return 'graph';
    if (DOCUMENT_DIALECTS.has(d))
        return 'document';
    if (VECTOR_DIALECTS.has(d))
        return 'vector';
    if (KEYVALUE_DIALECTS.has(d))
        return 'keyvalue';
    if (SEARCH_DIALECTS.has(d))
        return 'search';
    if (SAAS_DIALECTS.has(d))
        return 'saas';
    return 'sql';
}
export function isSqlDialect(d) {
    return SQL_DIALECTS.has(d);
}
export function isGraphDialect(d) {
    return GRAPH_DIALECTS.has(d);
}
export function isDocumentDialect(d) {
    return DOCUMENT_DIALECTS.has(d);
}
export function isVectorDialect(d) {
    return VECTOR_DIALECTS.has(d);
}
export function isKeyValueDialect(d) {
    return KEYVALUE_DIALECTS.has(d);
}
export function isSearchDialect(d) {
    return SEARCH_DIALECTS.has(d);
}
export function isSaasDialect(d) {
    return SAAS_DIALECTS.has(d);
}
export const DIALECT_META = {
    postgres: {
        dialect: 'postgres',
        label: 'PostgreSQL',
        kind: 'sql',
        defaultPort: 5432,
        brandColor: '#336791',
        usesNetwork: true,
        available: true,
    },
    mysql: {
        dialect: 'mysql',
        label: 'MySQL',
        kind: 'sql',
        defaultPort: 3306,
        brandColor: '#00758F',
        usesNetwork: true,
        available: true,
    },
    mariadb: {
        dialect: 'mariadb',
        label: 'MariaDB',
        kind: 'sql',
        defaultPort: 3306,
        brandColor: '#003545',
        usesNetwork: true,
        available: true,
    },
    mssql: {
        dialect: 'mssql',
        label: 'SQL Server',
        kind: 'sql',
        defaultPort: 1433,
        brandColor: '#A91D22',
        usesNetwork: true,
        available: true,
    },
    sqlite: {
        dialect: 'sqlite',
        label: 'SQLite',
        kind: 'sql',
        brandColor: '#003B57',
        usesNetwork: false,
        available: true,
    },
    cockroach: {
        dialect: 'cockroach',
        label: 'CockroachDB',
        kind: 'sql',
        defaultPort: 26257,
        brandColor: '#6933FF',
        usesNetwork: true,
        available: true,
    },
    oracle: {
        dialect: 'oracle',
        label: 'Oracle',
        kind: 'sql',
        defaultPort: 1521,
        brandColor: '#F80000',
        usesNetwork: true,
        available: true,
    },
    clickhouse: {
        dialect: 'clickhouse',
        label: 'ClickHouse',
        kind: 'sql',
        defaultPort: 8123,
        brandColor: '#FFCC01',
        usesNetwork: true,
        available: true,
    },
    duckdb: {
        dialect: 'duckdb',
        label: 'DuckDB',
        kind: 'sql',
        brandColor: '#FFF000',
        usesNetwork: false,
        available: true,
    },
    mongodb: {
        dialect: 'mongodb',
        label: 'MongoDB',
        kind: 'document',
        defaultPort: 27017,
        brandColor: '#13AA52',
        usesNetwork: true,
        available: true,
    },
    neo4j: {
        dialect: 'neo4j',
        label: 'Neo4j',
        kind: 'graph',
        defaultPort: 7687,
        brandColor: '#018BFF',
        usesNetwork: true,
        available: true,
    },
    falkordb: {
        dialect: 'falkordb',
        label: 'FalkorDB',
        kind: 'graph',
        defaultPort: 6379,
        brandColor: '#FF4438',
        usesNetwork: true,
        available: true,
    },
    ultipa: {
        dialect: 'ultipa',
        label: 'Ultipa',
        kind: 'graph',
        defaultPort: 60061,
        brandColor: '#7C3AED',
        usesNetwork: true,
        available: true,
        beta: true,
    },
    qdrant: {
        dialect: 'qdrant',
        label: 'Qdrant',
        kind: 'vector',
        defaultPort: 6333,
        brandColor: '#DC2626',
        usesNetwork: true,
        available: true,
    },
    redis: {
        dialect: 'redis',
        label: 'Redis',
        kind: 'keyvalue',
        defaultPort: 6379,
        brandColor: '#DC382D',
        usesNetwork: true,
        available: true,
    },
    elasticsearch: {
        dialect: 'elasticsearch',
        label: 'Elasticsearch',
        kind: 'search',
        defaultPort: 9200,
        brandColor: '#005571',
        usesNetwork: true,
        available: true,
    },
    salesforce: {
        dialect: 'salesforce',
        label: 'Salesforce',
        kind: 'saas',
        brandColor: '#00A1E0',
        usesNetwork: true,
        available: true,
        beta: true,
    },
    'salesforce-data-cloud': {
        dialect: 'salesforce-data-cloud',
        label: 'Salesforce Data Cloud',
        kind: 'saas',
        brandColor: '#032E61',
        usesNetwork: true,
        available: true,
        beta: true,
    },
};
//# sourceMappingURL=dialect.js.map