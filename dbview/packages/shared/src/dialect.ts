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
export type SqlDialect = z.infer<typeof SqlDialectSchema>;

export const GraphDialectSchema = z.enum(['neo4j', 'falkordb', 'ultipa']);
export type GraphDialect = z.infer<typeof GraphDialectSchema>;

export const DocumentDialectSchema = z.enum(['mongodb']);
export type DocumentDialect = z.infer<typeof DocumentDialectSchema>;

export const VectorDialectSchema = z.enum(['qdrant']);
export type VectorDialect = z.infer<typeof VectorDialectSchema>;

export const KeyValueDialectSchema = z.enum(['redis']);
export type KeyValueDialect = z.infer<typeof KeyValueDialectSchema>;

export const SearchDialectSchema = z.enum(['elasticsearch']);
export type SearchDialect = z.infer<typeof SearchDialectSchema>;

export const SaasDialectSchema = z.enum(['salesforce', 'salesforce-data-cloud']);
export type SaasDialect = z.infer<typeof SaasDialectSchema>;

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
export type Dialect = z.infer<typeof DialectSchema>;

export const SUPPORTED_DIALECTS: readonly Dialect[] = [
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
] as const;

export type DialectKind = 'sql' | 'graph' | 'document' | 'vector' | 'keyvalue' | 'search' | 'saas';

const SQL_DIALECTS = new Set<Dialect>([
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
const GRAPH_DIALECTS = new Set<Dialect>(['neo4j', 'falkordb', 'ultipa']);
const DOCUMENT_DIALECTS = new Set<Dialect>(['mongodb']);
const VECTOR_DIALECTS = new Set<Dialect>(['qdrant']);
const KEYVALUE_DIALECTS = new Set<Dialect>(['redis']);
const SEARCH_DIALECTS = new Set<Dialect>(['elasticsearch']);
const SAAS_DIALECTS = new Set<Dialect>(['salesforce', 'salesforce-data-cloud']);

export function dialectKind(d: Dialect): DialectKind {
  if (GRAPH_DIALECTS.has(d)) return 'graph';
  if (DOCUMENT_DIALECTS.has(d)) return 'document';
  if (VECTOR_DIALECTS.has(d)) return 'vector';
  if (KEYVALUE_DIALECTS.has(d)) return 'keyvalue';
  if (SEARCH_DIALECTS.has(d)) return 'search';
  if (SAAS_DIALECTS.has(d)) return 'saas';
  return 'sql';
}

export function isSqlDialect(d: Dialect): d is SqlDialect {
  return SQL_DIALECTS.has(d);
}

export function isGraphDialect(d: Dialect): d is GraphDialect {
  return GRAPH_DIALECTS.has(d);
}

export function isDocumentDialect(d: Dialect): d is DocumentDialect {
  return DOCUMENT_DIALECTS.has(d);
}

export function isVectorDialect(d: Dialect): d is VectorDialect {
  return VECTOR_DIALECTS.has(d);
}

export function isKeyValueDialect(d: Dialect): d is KeyValueDialect {
  return KEYVALUE_DIALECTS.has(d);
}

export function isSearchDialect(d: Dialect): d is SearchDialect {
  return SEARCH_DIALECTS.has(d);
}

export function isSaasDialect(d: Dialect): d is SaasDialect {
  return SAAS_DIALECTS.has(d);
}

export interface DialectMeta {
  dialect: Dialect;
  label: string;
  kind: DialectKind;
  defaultPort?: number;
  /** Brand color (foreground tint) for chips/headers. */
  brandColor: string;
  /** True when target uses host/port/user/pass; false for filesystem-backed. */
  usesNetwork: boolean;
  /** False when dialect appears in UI but engine not yet implemented. */
  available: boolean;
  /** Optional flag — engine is implemented but not yet production-hardened. */
  beta?: boolean;
}

export const DIALECT_META: Record<Dialect, DialectMeta> = {
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
