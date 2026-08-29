import { z } from 'zod';
export const ColumnSchema = z.object({
    name: z.string(),
    dataType: z.string(),
    nullable: z.boolean(),
    isPrimaryKey: z.boolean(),
    isForeignKey: z.boolean(),
    isUnique: z.boolean().default(false),
    defaultValue: z.string().nullable().optional(),
    /**
     * Optional human-readable label distinct from the technical column name.
     * Used by SaaS engines (Salesforce Data Cloud, Salesforce SObjects) where
     * the technical name (`ssot__HireDate__c`) carries little semantic signal
     * and the label ("Hire Date") is what the LLM needs to ground intent.
     */
    displayName: z.string().optional(),
    /** Optional human-readable description / business definition. */
    description: z.string().optional(),
});
export const TableNodeSchema = z.object({
    id: z.string(), // schema.table
    schema: z.string(),
    name: z.string(),
    columns: z.array(ColumnSchema),
    rowCountEstimate: z.number().int().nonnegative().optional(),
    /** Optional human-readable label distinct from the technical entity name. */
    displayName: z.string().optional(),
    /** Optional business description for the entity (purpose, source system). */
    description: z.string().optional(),
});
export const FKEdgeSchema = z.object({
    id: z.string(),
    source: z.string(), // table id
    sourceColumn: z.string(),
    target: z.string(), // table id
    targetColumn: z.string(),
    constraintName: z.string().optional(),
    onDelete: z.string().optional(),
    onUpdate: z.string().optional(),
});
export const SchemaGraphSchema = z.object({
    kind: z.literal('relational'),
    dialect: z.enum([
        'postgres',
        'mysql',
        'mariadb',
        'mssql',
        'sqlite',
        'cockroach',
        'oracle',
        'clickhouse',
        'duckdb',
        'salesforce',
        'salesforce-data-cloud',
    ]),
    tables: z.array(TableNodeSchema),
    edges: z.array(FKEdgeSchema),
    generatedAt: z.string().datetime(),
});
export const PropertyKeySchema = z.object({
    name: z.string(),
    types: z.array(z.string()),
    nullable: z.boolean(),
    /** Distinct sample values when cardinality is low (string-typed enums). */
    sampleValues: z.array(z.string()).optional(),
});
export const NodeLabelSchema = z.object({
    id: z.string(),
    label: z.string(),
    properties: z.array(PropertyKeySchema),
    count: z.number().int().nonnegative().optional(),
});
export const RelationshipTypeSchema = z.object({
    id: z.string(),
    type: z.string(),
    source: z.string(),
    target: z.string(),
    properties: z.array(PropertyKeySchema),
    count: z.number().int().nonnegative().optional(),
});
export const PropertyGraphSchemaSchema = z.object({
    kind: z.literal('graph'),
    dialect: z.enum(['neo4j', 'falkordb', 'ultipa']),
    labels: z.array(NodeLabelSchema),
    relationships: z.array(RelationshipTypeSchema),
    generatedAt: z.string().datetime(),
});
/**
 * Vector store collection — payload describes shape of stored points.
 */
export const VectorPayloadFieldSchema = z.object({
    name: z.string(),
    /** Detected JS types observed across sampled points (STRING/INTEGER/...). */
    types: z.array(z.string()),
    /** Distinct sample values when cardinality is low. */
    sampleValues: z.array(z.string()).optional(),
});
export const VectorCollectionSchema = z.object({
    id: z.string(),
    name: z.string(),
    vectorSize: z.number().int().nonnegative(),
    /** Distance metric: cosine | euclid | dot | manhattan. */
    distance: z.string(),
    pointCount: z.number().int().nonnegative().optional(),
    /** Named-vector configuration: each entry one named vector + its size. */
    namedVectors: z
        .array(z.object({ name: z.string(), size: z.number().int().nonnegative() }))
        .optional(),
    payloadFields: z.array(VectorPayloadFieldSchema),
});
export const VectorStoreSchemaSchema = z.object({
    kind: z.literal('vector'),
    dialect: z.enum(['qdrant']),
    collections: z.array(VectorCollectionSchema),
    generatedAt: z.string().datetime(),
});
/**
 * Key-value store schema — keys grouped by detected namespace prefix
 * (e.g. "user:*", "session:*"). Each group reports observed Redis types.
 */
export const KeyValueNamespaceSchema = z.object({
    /** Prefix pattern, e.g. `user:*` or `(no-prefix)` for keys without `:`. */
    pattern: z.string(),
    /** Distinct Redis types observed in this namespace (string/list/set/zset/hash/stream). */
    types: z.array(z.string()),
    /** Sampled key examples (truncated set). */
    sampleKeys: z.array(z.string()),
    /** Approximate count of keys matching this pattern. */
    keyCount: z.number().int().nonnegative(),
});
export const KeyValueStoreSchemaSchema = z.object({
    kind: z.literal('keyvalue'),
    dialect: z.enum(['redis']),
    /** Logical DB index (Redis: 0..15). */
    db: z.number().int().nonnegative(),
    /** Total observed key count (capped at sample limit). */
    totalKeys: z.number().int().nonnegative(),
    namespaces: z.array(KeyValueNamespaceSchema),
    generatedAt: z.string().datetime(),
});
/**
 * Search index field — flat path with detected ES mapping types.
 */
export const SearchIndexFieldSchema = z.object({
    /** Dotted JSON path (e.g. `user.address.city`). */
    name: z.string(),
    /** Elasticsearch field type (text/keyword/long/date/object/nested/etc.). */
    type: z.string(),
    /** True if field is analyzed text (full-text searchable). */
    analyzed: z.boolean().optional(),
});
export const SearchIndexSchema = z.object({
    id: z.string(),
    name: z.string(),
    /** Approximate doc count from /_stats. */
    docCount: z.number().int().nonnegative().optional(),
    /** Primary shard size bytes. */
    sizeBytes: z.number().int().nonnegative().optional(),
    aliases: z.array(z.string()),
    fields: z.array(SearchIndexFieldSchema),
});
export const SearchStoreSchemaSchema = z.object({
    kind: z.literal('search'),
    dialect: z.enum(['elasticsearch']),
    /** Cluster name as reported by /_cluster/health. */
    cluster: z.string().optional(),
    indices: z.array(SearchIndexSchema),
    generatedAt: z.string().datetime(),
});
/**
 * Document store schema — collections with inferred field structure from sampled docs.
 */
export const DocumentFieldSchema = z.object({
    /** Dotted path (e.g. `address.city`). */
    name: z.string(),
    /** Detected BSON types across sampled docs. */
    types: z.array(z.string()),
    /** Fraction of sampled docs containing this field (0..1). */
    presence: z.number().min(0).max(1).optional(),
    /** Sampled values when low cardinality (enum-like). */
    sampleValues: z.array(z.string()).optional(),
});
export const DocumentCollectionSchema = z.object({
    id: z.string(),
    /** Database name. */
    database: z.string(),
    /** Collection name. */
    name: z.string(),
    docCount: z.number().int().nonnegative().optional(),
    /** Approximate storage size in bytes. */
    sizeBytes: z.number().int().nonnegative().optional(),
    /** Index names defined on the collection (excluding _id). */
    indexes: z.array(z.string()),
    fields: z.array(DocumentFieldSchema),
});
export const DocumentStoreSchemaSchema = z.object({
    kind: z.literal('document'),
    dialect: z.enum(['mongodb']),
    /** Database the connection points to (default DB from URL). */
    database: z.string(),
    collections: z.array(DocumentCollectionSchema),
    generatedAt: z.string().datetime(),
});
export const UnifiedSchemaSchema = z.discriminatedUnion('kind', [
    SchemaGraphSchema,
    PropertyGraphSchemaSchema,
    VectorStoreSchemaSchema,
    KeyValueStoreSchemaSchema,
    SearchStoreSchemaSchema,
    DocumentStoreSchemaSchema,
]);
//# sourceMappingURL=schema-graph.js.map