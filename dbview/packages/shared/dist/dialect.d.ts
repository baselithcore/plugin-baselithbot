import { z } from 'zod';
export declare const SqlDialectSchema: z.ZodEnum<["postgres", "mysql", "mariadb", "mssql", "sqlite", "cockroach", "oracle", "clickhouse", "duckdb"]>;
export type SqlDialect = z.infer<typeof SqlDialectSchema>;
export declare const GraphDialectSchema: z.ZodEnum<["neo4j", "falkordb", "ultipa"]>;
export type GraphDialect = z.infer<typeof GraphDialectSchema>;
export declare const DocumentDialectSchema: z.ZodEnum<["mongodb"]>;
export type DocumentDialect = z.infer<typeof DocumentDialectSchema>;
export declare const VectorDialectSchema: z.ZodEnum<["qdrant"]>;
export type VectorDialect = z.infer<typeof VectorDialectSchema>;
export declare const KeyValueDialectSchema: z.ZodEnum<["redis"]>;
export type KeyValueDialect = z.infer<typeof KeyValueDialectSchema>;
export declare const SearchDialectSchema: z.ZodEnum<["elasticsearch"]>;
export type SearchDialect = z.infer<typeof SearchDialectSchema>;
export declare const SaasDialectSchema: z.ZodEnum<["salesforce", "salesforce-data-cloud"]>;
export type SaasDialect = z.infer<typeof SaasDialectSchema>;
export declare const DialectSchema: z.ZodEnum<["postgres", "mysql", "mariadb", "mssql", "sqlite", "cockroach", "oracle", "clickhouse", "duckdb", "mongodb", "neo4j", "falkordb", "ultipa", "qdrant", "redis", "elasticsearch", "salesforce", "salesforce-data-cloud"]>;
export type Dialect = z.infer<typeof DialectSchema>;
export declare const SUPPORTED_DIALECTS: readonly Dialect[];
export type DialectKind = 'sql' | 'graph' | 'document' | 'vector' | 'keyvalue' | 'search' | 'saas';
export declare function dialectKind(d: Dialect): DialectKind;
export declare function isSqlDialect(d: Dialect): d is SqlDialect;
export declare function isGraphDialect(d: Dialect): d is GraphDialect;
export declare function isDocumentDialect(d: Dialect): d is DocumentDialect;
export declare function isVectorDialect(d: Dialect): d is VectorDialect;
export declare function isKeyValueDialect(d: Dialect): d is KeyValueDialect;
export declare function isSearchDialect(d: Dialect): d is SearchDialect;
export declare function isSaasDialect(d: Dialect): d is SaasDialect;
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
export declare const DIALECT_META: Record<Dialect, DialectMeta>;
//# sourceMappingURL=dialect.d.ts.map