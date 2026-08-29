import { z } from 'zod';
export declare const ColumnSchema: z.ZodObject<{
    name: z.ZodString;
    dataType: z.ZodString;
    nullable: z.ZodBoolean;
    isPrimaryKey: z.ZodBoolean;
    isForeignKey: z.ZodBoolean;
    isUnique: z.ZodDefault<z.ZodBoolean>;
    defaultValue: z.ZodOptional<z.ZodNullable<z.ZodString>>;
    /**
     * Optional human-readable label distinct from the technical column name.
     * Used by SaaS engines (Salesforce Data Cloud, Salesforce SObjects) where
     * the technical name (`ssot__HireDate__c`) carries little semantic signal
     * and the label ("Hire Date") is what the LLM needs to ground intent.
     */
    displayName: z.ZodOptional<z.ZodString>;
    /** Optional human-readable description / business definition. */
    description: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    name: string;
    dataType: string;
    nullable: boolean;
    isPrimaryKey: boolean;
    isForeignKey: boolean;
    isUnique: boolean;
    displayName?: string | undefined;
    defaultValue?: string | null | undefined;
    description?: string | undefined;
}, {
    name: string;
    dataType: string;
    nullable: boolean;
    isPrimaryKey: boolean;
    isForeignKey: boolean;
    displayName?: string | undefined;
    isUnique?: boolean | undefined;
    defaultValue?: string | null | undefined;
    description?: string | undefined;
}>;
export type Column = z.infer<typeof ColumnSchema>;
export declare const TableNodeSchema: z.ZodObject<{
    id: z.ZodString;
    schema: z.ZodString;
    name: z.ZodString;
    columns: z.ZodArray<z.ZodObject<{
        name: z.ZodString;
        dataType: z.ZodString;
        nullable: z.ZodBoolean;
        isPrimaryKey: z.ZodBoolean;
        isForeignKey: z.ZodBoolean;
        isUnique: z.ZodDefault<z.ZodBoolean>;
        defaultValue: z.ZodOptional<z.ZodNullable<z.ZodString>>;
        /**
         * Optional human-readable label distinct from the technical column name.
         * Used by SaaS engines (Salesforce Data Cloud, Salesforce SObjects) where
         * the technical name (`ssot__HireDate__c`) carries little semantic signal
         * and the label ("Hire Date") is what the LLM needs to ground intent.
         */
        displayName: z.ZodOptional<z.ZodString>;
        /** Optional human-readable description / business definition. */
        description: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        name: string;
        dataType: string;
        nullable: boolean;
        isPrimaryKey: boolean;
        isForeignKey: boolean;
        isUnique: boolean;
        displayName?: string | undefined;
        defaultValue?: string | null | undefined;
        description?: string | undefined;
    }, {
        name: string;
        dataType: string;
        nullable: boolean;
        isPrimaryKey: boolean;
        isForeignKey: boolean;
        displayName?: string | undefined;
        isUnique?: boolean | undefined;
        defaultValue?: string | null | undefined;
        description?: string | undefined;
    }>, "many">;
    rowCountEstimate: z.ZodOptional<z.ZodNumber>;
    /** Optional human-readable label distinct from the technical entity name. */
    displayName: z.ZodOptional<z.ZodString>;
    /** Optional business description for the entity (purpose, source system). */
    description: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    id: string;
    name: string;
    columns: {
        name: string;
        dataType: string;
        nullable: boolean;
        isPrimaryKey: boolean;
        isForeignKey: boolean;
        isUnique: boolean;
        displayName?: string | undefined;
        defaultValue?: string | null | undefined;
        description?: string | undefined;
    }[];
    schema: string;
    displayName?: string | undefined;
    description?: string | undefined;
    rowCountEstimate?: number | undefined;
}, {
    id: string;
    name: string;
    columns: {
        name: string;
        dataType: string;
        nullable: boolean;
        isPrimaryKey: boolean;
        isForeignKey: boolean;
        displayName?: string | undefined;
        isUnique?: boolean | undefined;
        defaultValue?: string | null | undefined;
        description?: string | undefined;
    }[];
    schema: string;
    displayName?: string | undefined;
    description?: string | undefined;
    rowCountEstimate?: number | undefined;
}>;
export type TableNode = z.infer<typeof TableNodeSchema>;
export declare const FKEdgeSchema: z.ZodObject<{
    id: z.ZodString;
    source: z.ZodString;
    sourceColumn: z.ZodString;
    target: z.ZodString;
    targetColumn: z.ZodString;
    constraintName: z.ZodOptional<z.ZodString>;
    onDelete: z.ZodOptional<z.ZodString>;
    onUpdate: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    id: string;
    source: string;
    sourceColumn: string;
    target: string;
    targetColumn: string;
    constraintName?: string | undefined;
    onDelete?: string | undefined;
    onUpdate?: string | undefined;
}, {
    id: string;
    source: string;
    sourceColumn: string;
    target: string;
    targetColumn: string;
    constraintName?: string | undefined;
    onDelete?: string | undefined;
    onUpdate?: string | undefined;
}>;
export type FKEdge = z.infer<typeof FKEdgeSchema>;
export declare const SchemaGraphSchema: z.ZodObject<{
    kind: z.ZodLiteral<"relational">;
    dialect: z.ZodEnum<["postgres", "mysql", "mariadb", "mssql", "sqlite", "cockroach", "oracle", "clickhouse", "duckdb", "salesforce", "salesforce-data-cloud"]>;
    tables: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        schema: z.ZodString;
        name: z.ZodString;
        columns: z.ZodArray<z.ZodObject<{
            name: z.ZodString;
            dataType: z.ZodString;
            nullable: z.ZodBoolean;
            isPrimaryKey: z.ZodBoolean;
            isForeignKey: z.ZodBoolean;
            isUnique: z.ZodDefault<z.ZodBoolean>;
            defaultValue: z.ZodOptional<z.ZodNullable<z.ZodString>>;
            /**
             * Optional human-readable label distinct from the technical column name.
             * Used by SaaS engines (Salesforce Data Cloud, Salesforce SObjects) where
             * the technical name (`ssot__HireDate__c`) carries little semantic signal
             * and the label ("Hire Date") is what the LLM needs to ground intent.
             */
            displayName: z.ZodOptional<z.ZodString>;
            /** Optional human-readable description / business definition. */
            description: z.ZodOptional<z.ZodString>;
        }, "strip", z.ZodTypeAny, {
            name: string;
            dataType: string;
            nullable: boolean;
            isPrimaryKey: boolean;
            isForeignKey: boolean;
            isUnique: boolean;
            displayName?: string | undefined;
            defaultValue?: string | null | undefined;
            description?: string | undefined;
        }, {
            name: string;
            dataType: string;
            nullable: boolean;
            isPrimaryKey: boolean;
            isForeignKey: boolean;
            displayName?: string | undefined;
            isUnique?: boolean | undefined;
            defaultValue?: string | null | undefined;
            description?: string | undefined;
        }>, "many">;
        rowCountEstimate: z.ZodOptional<z.ZodNumber>;
        /** Optional human-readable label distinct from the technical entity name. */
        displayName: z.ZodOptional<z.ZodString>;
        /** Optional business description for the entity (purpose, source system). */
        description: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        name: string;
        columns: {
            name: string;
            dataType: string;
            nullable: boolean;
            isPrimaryKey: boolean;
            isForeignKey: boolean;
            isUnique: boolean;
            displayName?: string | undefined;
            defaultValue?: string | null | undefined;
            description?: string | undefined;
        }[];
        schema: string;
        displayName?: string | undefined;
        description?: string | undefined;
        rowCountEstimate?: number | undefined;
    }, {
        id: string;
        name: string;
        columns: {
            name: string;
            dataType: string;
            nullable: boolean;
            isPrimaryKey: boolean;
            isForeignKey: boolean;
            displayName?: string | undefined;
            isUnique?: boolean | undefined;
            defaultValue?: string | null | undefined;
            description?: string | undefined;
        }[];
        schema: string;
        displayName?: string | undefined;
        description?: string | undefined;
        rowCountEstimate?: number | undefined;
    }>, "many">;
    edges: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        source: z.ZodString;
        sourceColumn: z.ZodString;
        target: z.ZodString;
        targetColumn: z.ZodString;
        constraintName: z.ZodOptional<z.ZodString>;
        onDelete: z.ZodOptional<z.ZodString>;
        onUpdate: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        source: string;
        sourceColumn: string;
        target: string;
        targetColumn: string;
        constraintName?: string | undefined;
        onDelete?: string | undefined;
        onUpdate?: string | undefined;
    }, {
        id: string;
        source: string;
        sourceColumn: string;
        target: string;
        targetColumn: string;
        constraintName?: string | undefined;
        onDelete?: string | undefined;
        onUpdate?: string | undefined;
    }>, "many">;
    generatedAt: z.ZodString;
}, "strip", z.ZodTypeAny, {
    dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "salesforce" | "salesforce-data-cloud";
    tables: {
        id: string;
        name: string;
        columns: {
            name: string;
            dataType: string;
            nullable: boolean;
            isPrimaryKey: boolean;
            isForeignKey: boolean;
            isUnique: boolean;
            displayName?: string | undefined;
            defaultValue?: string | null | undefined;
            description?: string | undefined;
        }[];
        schema: string;
        displayName?: string | undefined;
        description?: string | undefined;
        rowCountEstimate?: number | undefined;
    }[];
    kind: "relational";
    edges: {
        id: string;
        source: string;
        sourceColumn: string;
        target: string;
        targetColumn: string;
        constraintName?: string | undefined;
        onDelete?: string | undefined;
        onUpdate?: string | undefined;
    }[];
    generatedAt: string;
}, {
    dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "salesforce" | "salesforce-data-cloud";
    tables: {
        id: string;
        name: string;
        columns: {
            name: string;
            dataType: string;
            nullable: boolean;
            isPrimaryKey: boolean;
            isForeignKey: boolean;
            displayName?: string | undefined;
            isUnique?: boolean | undefined;
            defaultValue?: string | null | undefined;
            description?: string | undefined;
        }[];
        schema: string;
        displayName?: string | undefined;
        description?: string | undefined;
        rowCountEstimate?: number | undefined;
    }[];
    kind: "relational";
    edges: {
        id: string;
        source: string;
        sourceColumn: string;
        target: string;
        targetColumn: string;
        constraintName?: string | undefined;
        onDelete?: string | undefined;
        onUpdate?: string | undefined;
    }[];
    generatedAt: string;
}>;
export type SchemaGraph = z.infer<typeof SchemaGraphSchema>;
export declare const PropertyKeySchema: z.ZodObject<{
    name: z.ZodString;
    types: z.ZodArray<z.ZodString, "many">;
    nullable: z.ZodBoolean;
    /** Distinct sample values when cardinality is low (string-typed enums). */
    sampleValues: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
}, "strip", z.ZodTypeAny, {
    name: string;
    nullable: boolean;
    types: string[];
    sampleValues?: string[] | undefined;
}, {
    name: string;
    nullable: boolean;
    types: string[];
    sampleValues?: string[] | undefined;
}>;
export type PropertyKey = z.infer<typeof PropertyKeySchema>;
export declare const NodeLabelSchema: z.ZodObject<{
    id: z.ZodString;
    label: z.ZodString;
    properties: z.ZodArray<z.ZodObject<{
        name: z.ZodString;
        types: z.ZodArray<z.ZodString, "many">;
        nullable: z.ZodBoolean;
        /** Distinct sample values when cardinality is low (string-typed enums). */
        sampleValues: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    }, "strip", z.ZodTypeAny, {
        name: string;
        nullable: boolean;
        types: string[];
        sampleValues?: string[] | undefined;
    }, {
        name: string;
        nullable: boolean;
        types: string[];
        sampleValues?: string[] | undefined;
    }>, "many">;
    count: z.ZodOptional<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    id: string;
    label: string;
    properties: {
        name: string;
        nullable: boolean;
        types: string[];
        sampleValues?: string[] | undefined;
    }[];
    count?: number | undefined;
}, {
    id: string;
    label: string;
    properties: {
        name: string;
        nullable: boolean;
        types: string[];
        sampleValues?: string[] | undefined;
    }[];
    count?: number | undefined;
}>;
export type NodeLabel = z.infer<typeof NodeLabelSchema>;
export declare const RelationshipTypeSchema: z.ZodObject<{
    id: z.ZodString;
    type: z.ZodString;
    source: z.ZodString;
    target: z.ZodString;
    properties: z.ZodArray<z.ZodObject<{
        name: z.ZodString;
        types: z.ZodArray<z.ZodString, "many">;
        nullable: z.ZodBoolean;
        /** Distinct sample values when cardinality is low (string-typed enums). */
        sampleValues: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    }, "strip", z.ZodTypeAny, {
        name: string;
        nullable: boolean;
        types: string[];
        sampleValues?: string[] | undefined;
    }, {
        name: string;
        nullable: boolean;
        types: string[];
        sampleValues?: string[] | undefined;
    }>, "many">;
    count: z.ZodOptional<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    type: string;
    id: string;
    source: string;
    target: string;
    properties: {
        name: string;
        nullable: boolean;
        types: string[];
        sampleValues?: string[] | undefined;
    }[];
    count?: number | undefined;
}, {
    type: string;
    id: string;
    source: string;
    target: string;
    properties: {
        name: string;
        nullable: boolean;
        types: string[];
        sampleValues?: string[] | undefined;
    }[];
    count?: number | undefined;
}>;
export type RelationshipType = z.infer<typeof RelationshipTypeSchema>;
export declare const PropertyGraphSchemaSchema: z.ZodObject<{
    kind: z.ZodLiteral<"graph">;
    dialect: z.ZodEnum<["neo4j", "falkordb", "ultipa"]>;
    labels: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        label: z.ZodString;
        properties: z.ZodArray<z.ZodObject<{
            name: z.ZodString;
            types: z.ZodArray<z.ZodString, "many">;
            nullable: z.ZodBoolean;
            /** Distinct sample values when cardinality is low (string-typed enums). */
            sampleValues: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
        }, "strip", z.ZodTypeAny, {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }, {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }>, "many">;
        count: z.ZodOptional<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        label: string;
        properties: {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        count?: number | undefined;
    }, {
        id: string;
        label: string;
        properties: {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        count?: number | undefined;
    }>, "many">;
    relationships: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        type: z.ZodString;
        source: z.ZodString;
        target: z.ZodString;
        properties: z.ZodArray<z.ZodObject<{
            name: z.ZodString;
            types: z.ZodArray<z.ZodString, "many">;
            nullable: z.ZodBoolean;
            /** Distinct sample values when cardinality is low (string-typed enums). */
            sampleValues: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
        }, "strip", z.ZodTypeAny, {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }, {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }>, "many">;
        count: z.ZodOptional<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        type: string;
        id: string;
        source: string;
        target: string;
        properties: {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        count?: number | undefined;
    }, {
        type: string;
        id: string;
        source: string;
        target: string;
        properties: {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        count?: number | undefined;
    }>, "many">;
    generatedAt: z.ZodString;
}, "strip", z.ZodTypeAny, {
    dialect: "neo4j" | "falkordb" | "ultipa";
    kind: "graph";
    generatedAt: string;
    labels: {
        id: string;
        label: string;
        properties: {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        count?: number | undefined;
    }[];
    relationships: {
        type: string;
        id: string;
        source: string;
        target: string;
        properties: {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        count?: number | undefined;
    }[];
}, {
    dialect: "neo4j" | "falkordb" | "ultipa";
    kind: "graph";
    generatedAt: string;
    labels: {
        id: string;
        label: string;
        properties: {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        count?: number | undefined;
    }[];
    relationships: {
        type: string;
        id: string;
        source: string;
        target: string;
        properties: {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        count?: number | undefined;
    }[];
}>;
export type PropertyGraphSchema = z.infer<typeof PropertyGraphSchemaSchema>;
/**
 * Vector store collection — payload describes shape of stored points.
 */
export declare const VectorPayloadFieldSchema: z.ZodObject<{
    name: z.ZodString;
    /** Detected JS types observed across sampled points (STRING/INTEGER/...). */
    types: z.ZodArray<z.ZodString, "many">;
    /** Distinct sample values when cardinality is low. */
    sampleValues: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
}, "strip", z.ZodTypeAny, {
    name: string;
    types: string[];
    sampleValues?: string[] | undefined;
}, {
    name: string;
    types: string[];
    sampleValues?: string[] | undefined;
}>;
export type VectorPayloadField = z.infer<typeof VectorPayloadFieldSchema>;
export declare const VectorCollectionSchema: z.ZodObject<{
    id: z.ZodString;
    name: z.ZodString;
    vectorSize: z.ZodNumber;
    /** Distance metric: cosine | euclid | dot | manhattan. */
    distance: z.ZodString;
    pointCount: z.ZodOptional<z.ZodNumber>;
    /** Named-vector configuration: each entry one named vector + its size. */
    namedVectors: z.ZodOptional<z.ZodArray<z.ZodObject<{
        name: z.ZodString;
        size: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        name: string;
        size: number;
    }, {
        name: string;
        size: number;
    }>, "many">>;
    payloadFields: z.ZodArray<z.ZodObject<{
        name: z.ZodString;
        /** Detected JS types observed across sampled points (STRING/INTEGER/...). */
        types: z.ZodArray<z.ZodString, "many">;
        /** Distinct sample values when cardinality is low. */
        sampleValues: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    }, "strip", z.ZodTypeAny, {
        name: string;
        types: string[];
        sampleValues?: string[] | undefined;
    }, {
        name: string;
        types: string[];
        sampleValues?: string[] | undefined;
    }>, "many">;
}, "strip", z.ZodTypeAny, {
    id: string;
    name: string;
    vectorSize: number;
    distance: string;
    payloadFields: {
        name: string;
        types: string[];
        sampleValues?: string[] | undefined;
    }[];
    pointCount?: number | undefined;
    namedVectors?: {
        name: string;
        size: number;
    }[] | undefined;
}, {
    id: string;
    name: string;
    vectorSize: number;
    distance: string;
    payloadFields: {
        name: string;
        types: string[];
        sampleValues?: string[] | undefined;
    }[];
    pointCount?: number | undefined;
    namedVectors?: {
        name: string;
        size: number;
    }[] | undefined;
}>;
export type VectorCollection = z.infer<typeof VectorCollectionSchema>;
export declare const VectorStoreSchemaSchema: z.ZodObject<{
    kind: z.ZodLiteral<"vector">;
    dialect: z.ZodEnum<["qdrant"]>;
    collections: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        name: z.ZodString;
        vectorSize: z.ZodNumber;
        /** Distance metric: cosine | euclid | dot | manhattan. */
        distance: z.ZodString;
        pointCount: z.ZodOptional<z.ZodNumber>;
        /** Named-vector configuration: each entry one named vector + its size. */
        namedVectors: z.ZodOptional<z.ZodArray<z.ZodObject<{
            name: z.ZodString;
            size: z.ZodNumber;
        }, "strip", z.ZodTypeAny, {
            name: string;
            size: number;
        }, {
            name: string;
            size: number;
        }>, "many">>;
        payloadFields: z.ZodArray<z.ZodObject<{
            name: z.ZodString;
            /** Detected JS types observed across sampled points (STRING/INTEGER/...). */
            types: z.ZodArray<z.ZodString, "many">;
            /** Distinct sample values when cardinality is low. */
            sampleValues: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
        }, "strip", z.ZodTypeAny, {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
        }, {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
        }>, "many">;
    }, "strip", z.ZodTypeAny, {
        id: string;
        name: string;
        vectorSize: number;
        distance: string;
        payloadFields: {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        pointCount?: number | undefined;
        namedVectors?: {
            name: string;
            size: number;
        }[] | undefined;
    }, {
        id: string;
        name: string;
        vectorSize: number;
        distance: string;
        payloadFields: {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        pointCount?: number | undefined;
        namedVectors?: {
            name: string;
            size: number;
        }[] | undefined;
    }>, "many">;
    generatedAt: z.ZodString;
}, "strip", z.ZodTypeAny, {
    dialect: "qdrant";
    kind: "vector";
    generatedAt: string;
    collections: {
        id: string;
        name: string;
        vectorSize: number;
        distance: string;
        payloadFields: {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        pointCount?: number | undefined;
        namedVectors?: {
            name: string;
            size: number;
        }[] | undefined;
    }[];
}, {
    dialect: "qdrant";
    kind: "vector";
    generatedAt: string;
    collections: {
        id: string;
        name: string;
        vectorSize: number;
        distance: string;
        payloadFields: {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        pointCount?: number | undefined;
        namedVectors?: {
            name: string;
            size: number;
        }[] | undefined;
    }[];
}>;
export type VectorStoreSchema = z.infer<typeof VectorStoreSchemaSchema>;
/**
 * Key-value store schema — keys grouped by detected namespace prefix
 * (e.g. "user:*", "session:*"). Each group reports observed Redis types.
 */
export declare const KeyValueNamespaceSchema: z.ZodObject<{
    /** Prefix pattern, e.g. `user:*` or `(no-prefix)` for keys without `:`. */
    pattern: z.ZodString;
    /** Distinct Redis types observed in this namespace (string/list/set/zset/hash/stream). */
    types: z.ZodArray<z.ZodString, "many">;
    /** Sampled key examples (truncated set). */
    sampleKeys: z.ZodArray<z.ZodString, "many">;
    /** Approximate count of keys matching this pattern. */
    keyCount: z.ZodNumber;
}, "strip", z.ZodTypeAny, {
    types: string[];
    pattern: string;
    sampleKeys: string[];
    keyCount: number;
}, {
    types: string[];
    pattern: string;
    sampleKeys: string[];
    keyCount: number;
}>;
export type KeyValueNamespace = z.infer<typeof KeyValueNamespaceSchema>;
export declare const KeyValueStoreSchemaSchema: z.ZodObject<{
    kind: z.ZodLiteral<"keyvalue">;
    dialect: z.ZodEnum<["redis"]>;
    /** Logical DB index (Redis: 0..15). */
    db: z.ZodNumber;
    /** Total observed key count (capped at sample limit). */
    totalKeys: z.ZodNumber;
    namespaces: z.ZodArray<z.ZodObject<{
        /** Prefix pattern, e.g. `user:*` or `(no-prefix)` for keys without `:`. */
        pattern: z.ZodString;
        /** Distinct Redis types observed in this namespace (string/list/set/zset/hash/stream). */
        types: z.ZodArray<z.ZodString, "many">;
        /** Sampled key examples (truncated set). */
        sampleKeys: z.ZodArray<z.ZodString, "many">;
        /** Approximate count of keys matching this pattern. */
        keyCount: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        types: string[];
        pattern: string;
        sampleKeys: string[];
        keyCount: number;
    }, {
        types: string[];
        pattern: string;
        sampleKeys: string[];
        keyCount: number;
    }>, "many">;
    generatedAt: z.ZodString;
}, "strip", z.ZodTypeAny, {
    dialect: "redis";
    db: number;
    kind: "keyvalue";
    generatedAt: string;
    totalKeys: number;
    namespaces: {
        types: string[];
        pattern: string;
        sampleKeys: string[];
        keyCount: number;
    }[];
}, {
    dialect: "redis";
    db: number;
    kind: "keyvalue";
    generatedAt: string;
    totalKeys: number;
    namespaces: {
        types: string[];
        pattern: string;
        sampleKeys: string[];
        keyCount: number;
    }[];
}>;
export type KeyValueStoreSchema = z.infer<typeof KeyValueStoreSchemaSchema>;
/**
 * Search index field — flat path with detected ES mapping types.
 */
export declare const SearchIndexFieldSchema: z.ZodObject<{
    /** Dotted JSON path (e.g. `user.address.city`). */
    name: z.ZodString;
    /** Elasticsearch field type (text/keyword/long/date/object/nested/etc.). */
    type: z.ZodString;
    /** True if field is analyzed text (full-text searchable). */
    analyzed: z.ZodOptional<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    type: string;
    name: string;
    analyzed?: boolean | undefined;
}, {
    type: string;
    name: string;
    analyzed?: boolean | undefined;
}>;
export type SearchIndexField = z.infer<typeof SearchIndexFieldSchema>;
export declare const SearchIndexSchema: z.ZodObject<{
    id: z.ZodString;
    name: z.ZodString;
    /** Approximate doc count from /_stats. */
    docCount: z.ZodOptional<z.ZodNumber>;
    /** Primary shard size bytes. */
    sizeBytes: z.ZodOptional<z.ZodNumber>;
    aliases: z.ZodArray<z.ZodString, "many">;
    fields: z.ZodArray<z.ZodObject<{
        /** Dotted JSON path (e.g. `user.address.city`). */
        name: z.ZodString;
        /** Elasticsearch field type (text/keyword/long/date/object/nested/etc.). */
        type: z.ZodString;
        /** True if field is analyzed text (full-text searchable). */
        analyzed: z.ZodOptional<z.ZodBoolean>;
    }, "strip", z.ZodTypeAny, {
        type: string;
        name: string;
        analyzed?: boolean | undefined;
    }, {
        type: string;
        name: string;
        analyzed?: boolean | undefined;
    }>, "many">;
}, "strip", z.ZodTypeAny, {
    id: string;
    name: string;
    aliases: string[];
    fields: {
        type: string;
        name: string;
        analyzed?: boolean | undefined;
    }[];
    sizeBytes?: number | undefined;
    docCount?: number | undefined;
}, {
    id: string;
    name: string;
    aliases: string[];
    fields: {
        type: string;
        name: string;
        analyzed?: boolean | undefined;
    }[];
    sizeBytes?: number | undefined;
    docCount?: number | undefined;
}>;
export type SearchIndex = z.infer<typeof SearchIndexSchema>;
export declare const SearchStoreSchemaSchema: z.ZodObject<{
    kind: z.ZodLiteral<"search">;
    dialect: z.ZodEnum<["elasticsearch"]>;
    /** Cluster name as reported by /_cluster/health. */
    cluster: z.ZodOptional<z.ZodString>;
    indices: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        name: z.ZodString;
        /** Approximate doc count from /_stats. */
        docCount: z.ZodOptional<z.ZodNumber>;
        /** Primary shard size bytes. */
        sizeBytes: z.ZodOptional<z.ZodNumber>;
        aliases: z.ZodArray<z.ZodString, "many">;
        fields: z.ZodArray<z.ZodObject<{
            /** Dotted JSON path (e.g. `user.address.city`). */
            name: z.ZodString;
            /** Elasticsearch field type (text/keyword/long/date/object/nested/etc.). */
            type: z.ZodString;
            /** True if field is analyzed text (full-text searchable). */
            analyzed: z.ZodOptional<z.ZodBoolean>;
        }, "strip", z.ZodTypeAny, {
            type: string;
            name: string;
            analyzed?: boolean | undefined;
        }, {
            type: string;
            name: string;
            analyzed?: boolean | undefined;
        }>, "many">;
    }, "strip", z.ZodTypeAny, {
        id: string;
        name: string;
        aliases: string[];
        fields: {
            type: string;
            name: string;
            analyzed?: boolean | undefined;
        }[];
        sizeBytes?: number | undefined;
        docCount?: number | undefined;
    }, {
        id: string;
        name: string;
        aliases: string[];
        fields: {
            type: string;
            name: string;
            analyzed?: boolean | undefined;
        }[];
        sizeBytes?: number | undefined;
        docCount?: number | undefined;
    }>, "many">;
    generatedAt: z.ZodString;
}, "strip", z.ZodTypeAny, {
    dialect: "elasticsearch";
    kind: "search";
    generatedAt: string;
    indices: {
        id: string;
        name: string;
        aliases: string[];
        fields: {
            type: string;
            name: string;
            analyzed?: boolean | undefined;
        }[];
        sizeBytes?: number | undefined;
        docCount?: number | undefined;
    }[];
    cluster?: string | undefined;
}, {
    dialect: "elasticsearch";
    kind: "search";
    generatedAt: string;
    indices: {
        id: string;
        name: string;
        aliases: string[];
        fields: {
            type: string;
            name: string;
            analyzed?: boolean | undefined;
        }[];
        sizeBytes?: number | undefined;
        docCount?: number | undefined;
    }[];
    cluster?: string | undefined;
}>;
export type SearchStoreSchema = z.infer<typeof SearchStoreSchemaSchema>;
/**
 * Document store schema — collections with inferred field structure from sampled docs.
 */
export declare const DocumentFieldSchema: z.ZodObject<{
    /** Dotted path (e.g. `address.city`). */
    name: z.ZodString;
    /** Detected BSON types across sampled docs. */
    types: z.ZodArray<z.ZodString, "many">;
    /** Fraction of sampled docs containing this field (0..1). */
    presence: z.ZodOptional<z.ZodNumber>;
    /** Sampled values when low cardinality (enum-like). */
    sampleValues: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
}, "strip", z.ZodTypeAny, {
    name: string;
    types: string[];
    sampleValues?: string[] | undefined;
    presence?: number | undefined;
}, {
    name: string;
    types: string[];
    sampleValues?: string[] | undefined;
    presence?: number | undefined;
}>;
export type DocumentField = z.infer<typeof DocumentFieldSchema>;
export declare const DocumentCollectionSchema: z.ZodObject<{
    id: z.ZodString;
    /** Database name. */
    database: z.ZodString;
    /** Collection name. */
    name: z.ZodString;
    docCount: z.ZodOptional<z.ZodNumber>;
    /** Approximate storage size in bytes. */
    sizeBytes: z.ZodOptional<z.ZodNumber>;
    /** Index names defined on the collection (excluding _id). */
    indexes: z.ZodArray<z.ZodString, "many">;
    fields: z.ZodArray<z.ZodObject<{
        /** Dotted path (e.g. `address.city`). */
        name: z.ZodString;
        /** Detected BSON types across sampled docs. */
        types: z.ZodArray<z.ZodString, "many">;
        /** Fraction of sampled docs containing this field (0..1). */
        presence: z.ZodOptional<z.ZodNumber>;
        /** Sampled values when low cardinality (enum-like). */
        sampleValues: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    }, "strip", z.ZodTypeAny, {
        name: string;
        types: string[];
        sampleValues?: string[] | undefined;
        presence?: number | undefined;
    }, {
        name: string;
        types: string[];
        sampleValues?: string[] | undefined;
        presence?: number | undefined;
    }>, "many">;
}, "strip", z.ZodTypeAny, {
    id: string;
    database: string;
    name: string;
    fields: {
        name: string;
        types: string[];
        sampleValues?: string[] | undefined;
        presence?: number | undefined;
    }[];
    indexes: string[];
    sizeBytes?: number | undefined;
    docCount?: number | undefined;
}, {
    id: string;
    database: string;
    name: string;
    fields: {
        name: string;
        types: string[];
        sampleValues?: string[] | undefined;
        presence?: number | undefined;
    }[];
    indexes: string[];
    sizeBytes?: number | undefined;
    docCount?: number | undefined;
}>;
export type DocumentCollection = z.infer<typeof DocumentCollectionSchema>;
export declare const DocumentStoreSchemaSchema: z.ZodObject<{
    kind: z.ZodLiteral<"document">;
    dialect: z.ZodEnum<["mongodb"]>;
    /** Database the connection points to (default DB from URL). */
    database: z.ZodString;
    collections: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        /** Database name. */
        database: z.ZodString;
        /** Collection name. */
        name: z.ZodString;
        docCount: z.ZodOptional<z.ZodNumber>;
        /** Approximate storage size in bytes. */
        sizeBytes: z.ZodOptional<z.ZodNumber>;
        /** Index names defined on the collection (excluding _id). */
        indexes: z.ZodArray<z.ZodString, "many">;
        fields: z.ZodArray<z.ZodObject<{
            /** Dotted path (e.g. `address.city`). */
            name: z.ZodString;
            /** Detected BSON types across sampled docs. */
            types: z.ZodArray<z.ZodString, "many">;
            /** Fraction of sampled docs containing this field (0..1). */
            presence: z.ZodOptional<z.ZodNumber>;
            /** Sampled values when low cardinality (enum-like). */
            sampleValues: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
        }, "strip", z.ZodTypeAny, {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
            presence?: number | undefined;
        }, {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
            presence?: number | undefined;
        }>, "many">;
    }, "strip", z.ZodTypeAny, {
        id: string;
        database: string;
        name: string;
        fields: {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
            presence?: number | undefined;
        }[];
        indexes: string[];
        sizeBytes?: number | undefined;
        docCount?: number | undefined;
    }, {
        id: string;
        database: string;
        name: string;
        fields: {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
            presence?: number | undefined;
        }[];
        indexes: string[];
        sizeBytes?: number | undefined;
        docCount?: number | undefined;
    }>, "many">;
    generatedAt: z.ZodString;
}, "strip", z.ZodTypeAny, {
    database: string;
    dialect: "mongodb";
    kind: "document";
    generatedAt: string;
    collections: {
        id: string;
        database: string;
        name: string;
        fields: {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
            presence?: number | undefined;
        }[];
        indexes: string[];
        sizeBytes?: number | undefined;
        docCount?: number | undefined;
    }[];
}, {
    database: string;
    dialect: "mongodb";
    kind: "document";
    generatedAt: string;
    collections: {
        id: string;
        database: string;
        name: string;
        fields: {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
            presence?: number | undefined;
        }[];
        indexes: string[];
        sizeBytes?: number | undefined;
        docCount?: number | undefined;
    }[];
}>;
export type DocumentStoreSchema = z.infer<typeof DocumentStoreSchemaSchema>;
export declare const UnifiedSchemaSchema: z.ZodDiscriminatedUnion<"kind", [z.ZodObject<{
    kind: z.ZodLiteral<"relational">;
    dialect: z.ZodEnum<["postgres", "mysql", "mariadb", "mssql", "sqlite", "cockroach", "oracle", "clickhouse", "duckdb", "salesforce", "salesforce-data-cloud"]>;
    tables: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        schema: z.ZodString;
        name: z.ZodString;
        columns: z.ZodArray<z.ZodObject<{
            name: z.ZodString;
            dataType: z.ZodString;
            nullable: z.ZodBoolean;
            isPrimaryKey: z.ZodBoolean;
            isForeignKey: z.ZodBoolean;
            isUnique: z.ZodDefault<z.ZodBoolean>;
            defaultValue: z.ZodOptional<z.ZodNullable<z.ZodString>>;
            /**
             * Optional human-readable label distinct from the technical column name.
             * Used by SaaS engines (Salesforce Data Cloud, Salesforce SObjects) where
             * the technical name (`ssot__HireDate__c`) carries little semantic signal
             * and the label ("Hire Date") is what the LLM needs to ground intent.
             */
            displayName: z.ZodOptional<z.ZodString>;
            /** Optional human-readable description / business definition. */
            description: z.ZodOptional<z.ZodString>;
        }, "strip", z.ZodTypeAny, {
            name: string;
            dataType: string;
            nullable: boolean;
            isPrimaryKey: boolean;
            isForeignKey: boolean;
            isUnique: boolean;
            displayName?: string | undefined;
            defaultValue?: string | null | undefined;
            description?: string | undefined;
        }, {
            name: string;
            dataType: string;
            nullable: boolean;
            isPrimaryKey: boolean;
            isForeignKey: boolean;
            displayName?: string | undefined;
            isUnique?: boolean | undefined;
            defaultValue?: string | null | undefined;
            description?: string | undefined;
        }>, "many">;
        rowCountEstimate: z.ZodOptional<z.ZodNumber>;
        /** Optional human-readable label distinct from the technical entity name. */
        displayName: z.ZodOptional<z.ZodString>;
        /** Optional business description for the entity (purpose, source system). */
        description: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        name: string;
        columns: {
            name: string;
            dataType: string;
            nullable: boolean;
            isPrimaryKey: boolean;
            isForeignKey: boolean;
            isUnique: boolean;
            displayName?: string | undefined;
            defaultValue?: string | null | undefined;
            description?: string | undefined;
        }[];
        schema: string;
        displayName?: string | undefined;
        description?: string | undefined;
        rowCountEstimate?: number | undefined;
    }, {
        id: string;
        name: string;
        columns: {
            name: string;
            dataType: string;
            nullable: boolean;
            isPrimaryKey: boolean;
            isForeignKey: boolean;
            displayName?: string | undefined;
            isUnique?: boolean | undefined;
            defaultValue?: string | null | undefined;
            description?: string | undefined;
        }[];
        schema: string;
        displayName?: string | undefined;
        description?: string | undefined;
        rowCountEstimate?: number | undefined;
    }>, "many">;
    edges: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        source: z.ZodString;
        sourceColumn: z.ZodString;
        target: z.ZodString;
        targetColumn: z.ZodString;
        constraintName: z.ZodOptional<z.ZodString>;
        onDelete: z.ZodOptional<z.ZodString>;
        onUpdate: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        source: string;
        sourceColumn: string;
        target: string;
        targetColumn: string;
        constraintName?: string | undefined;
        onDelete?: string | undefined;
        onUpdate?: string | undefined;
    }, {
        id: string;
        source: string;
        sourceColumn: string;
        target: string;
        targetColumn: string;
        constraintName?: string | undefined;
        onDelete?: string | undefined;
        onUpdate?: string | undefined;
    }>, "many">;
    generatedAt: z.ZodString;
}, "strip", z.ZodTypeAny, {
    dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "salesforce" | "salesforce-data-cloud";
    tables: {
        id: string;
        name: string;
        columns: {
            name: string;
            dataType: string;
            nullable: boolean;
            isPrimaryKey: boolean;
            isForeignKey: boolean;
            isUnique: boolean;
            displayName?: string | undefined;
            defaultValue?: string | null | undefined;
            description?: string | undefined;
        }[];
        schema: string;
        displayName?: string | undefined;
        description?: string | undefined;
        rowCountEstimate?: number | undefined;
    }[];
    kind: "relational";
    edges: {
        id: string;
        source: string;
        sourceColumn: string;
        target: string;
        targetColumn: string;
        constraintName?: string | undefined;
        onDelete?: string | undefined;
        onUpdate?: string | undefined;
    }[];
    generatedAt: string;
}, {
    dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "salesforce" | "salesforce-data-cloud";
    tables: {
        id: string;
        name: string;
        columns: {
            name: string;
            dataType: string;
            nullable: boolean;
            isPrimaryKey: boolean;
            isForeignKey: boolean;
            displayName?: string | undefined;
            isUnique?: boolean | undefined;
            defaultValue?: string | null | undefined;
            description?: string | undefined;
        }[];
        schema: string;
        displayName?: string | undefined;
        description?: string | undefined;
        rowCountEstimate?: number | undefined;
    }[];
    kind: "relational";
    edges: {
        id: string;
        source: string;
        sourceColumn: string;
        target: string;
        targetColumn: string;
        constraintName?: string | undefined;
        onDelete?: string | undefined;
        onUpdate?: string | undefined;
    }[];
    generatedAt: string;
}>, z.ZodObject<{
    kind: z.ZodLiteral<"graph">;
    dialect: z.ZodEnum<["neo4j", "falkordb", "ultipa"]>;
    labels: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        label: z.ZodString;
        properties: z.ZodArray<z.ZodObject<{
            name: z.ZodString;
            types: z.ZodArray<z.ZodString, "many">;
            nullable: z.ZodBoolean;
            /** Distinct sample values when cardinality is low (string-typed enums). */
            sampleValues: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
        }, "strip", z.ZodTypeAny, {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }, {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }>, "many">;
        count: z.ZodOptional<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        label: string;
        properties: {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        count?: number | undefined;
    }, {
        id: string;
        label: string;
        properties: {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        count?: number | undefined;
    }>, "many">;
    relationships: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        type: z.ZodString;
        source: z.ZodString;
        target: z.ZodString;
        properties: z.ZodArray<z.ZodObject<{
            name: z.ZodString;
            types: z.ZodArray<z.ZodString, "many">;
            nullable: z.ZodBoolean;
            /** Distinct sample values when cardinality is low (string-typed enums). */
            sampleValues: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
        }, "strip", z.ZodTypeAny, {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }, {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }>, "many">;
        count: z.ZodOptional<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        type: string;
        id: string;
        source: string;
        target: string;
        properties: {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        count?: number | undefined;
    }, {
        type: string;
        id: string;
        source: string;
        target: string;
        properties: {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        count?: number | undefined;
    }>, "many">;
    generatedAt: z.ZodString;
}, "strip", z.ZodTypeAny, {
    dialect: "neo4j" | "falkordb" | "ultipa";
    kind: "graph";
    generatedAt: string;
    labels: {
        id: string;
        label: string;
        properties: {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        count?: number | undefined;
    }[];
    relationships: {
        type: string;
        id: string;
        source: string;
        target: string;
        properties: {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        count?: number | undefined;
    }[];
}, {
    dialect: "neo4j" | "falkordb" | "ultipa";
    kind: "graph";
    generatedAt: string;
    labels: {
        id: string;
        label: string;
        properties: {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        count?: number | undefined;
    }[];
    relationships: {
        type: string;
        id: string;
        source: string;
        target: string;
        properties: {
            name: string;
            nullable: boolean;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        count?: number | undefined;
    }[];
}>, z.ZodObject<{
    kind: z.ZodLiteral<"vector">;
    dialect: z.ZodEnum<["qdrant"]>;
    collections: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        name: z.ZodString;
        vectorSize: z.ZodNumber;
        /** Distance metric: cosine | euclid | dot | manhattan. */
        distance: z.ZodString;
        pointCount: z.ZodOptional<z.ZodNumber>;
        /** Named-vector configuration: each entry one named vector + its size. */
        namedVectors: z.ZodOptional<z.ZodArray<z.ZodObject<{
            name: z.ZodString;
            size: z.ZodNumber;
        }, "strip", z.ZodTypeAny, {
            name: string;
            size: number;
        }, {
            name: string;
            size: number;
        }>, "many">>;
        payloadFields: z.ZodArray<z.ZodObject<{
            name: z.ZodString;
            /** Detected JS types observed across sampled points (STRING/INTEGER/...). */
            types: z.ZodArray<z.ZodString, "many">;
            /** Distinct sample values when cardinality is low. */
            sampleValues: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
        }, "strip", z.ZodTypeAny, {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
        }, {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
        }>, "many">;
    }, "strip", z.ZodTypeAny, {
        id: string;
        name: string;
        vectorSize: number;
        distance: string;
        payloadFields: {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        pointCount?: number | undefined;
        namedVectors?: {
            name: string;
            size: number;
        }[] | undefined;
    }, {
        id: string;
        name: string;
        vectorSize: number;
        distance: string;
        payloadFields: {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        pointCount?: number | undefined;
        namedVectors?: {
            name: string;
            size: number;
        }[] | undefined;
    }>, "many">;
    generatedAt: z.ZodString;
}, "strip", z.ZodTypeAny, {
    dialect: "qdrant";
    kind: "vector";
    generatedAt: string;
    collections: {
        id: string;
        name: string;
        vectorSize: number;
        distance: string;
        payloadFields: {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        pointCount?: number | undefined;
        namedVectors?: {
            name: string;
            size: number;
        }[] | undefined;
    }[];
}, {
    dialect: "qdrant";
    kind: "vector";
    generatedAt: string;
    collections: {
        id: string;
        name: string;
        vectorSize: number;
        distance: string;
        payloadFields: {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
        }[];
        pointCount?: number | undefined;
        namedVectors?: {
            name: string;
            size: number;
        }[] | undefined;
    }[];
}>, z.ZodObject<{
    kind: z.ZodLiteral<"keyvalue">;
    dialect: z.ZodEnum<["redis"]>;
    /** Logical DB index (Redis: 0..15). */
    db: z.ZodNumber;
    /** Total observed key count (capped at sample limit). */
    totalKeys: z.ZodNumber;
    namespaces: z.ZodArray<z.ZodObject<{
        /** Prefix pattern, e.g. `user:*` or `(no-prefix)` for keys without `:`. */
        pattern: z.ZodString;
        /** Distinct Redis types observed in this namespace (string/list/set/zset/hash/stream). */
        types: z.ZodArray<z.ZodString, "many">;
        /** Sampled key examples (truncated set). */
        sampleKeys: z.ZodArray<z.ZodString, "many">;
        /** Approximate count of keys matching this pattern. */
        keyCount: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        types: string[];
        pattern: string;
        sampleKeys: string[];
        keyCount: number;
    }, {
        types: string[];
        pattern: string;
        sampleKeys: string[];
        keyCount: number;
    }>, "many">;
    generatedAt: z.ZodString;
}, "strip", z.ZodTypeAny, {
    dialect: "redis";
    db: number;
    kind: "keyvalue";
    generatedAt: string;
    totalKeys: number;
    namespaces: {
        types: string[];
        pattern: string;
        sampleKeys: string[];
        keyCount: number;
    }[];
}, {
    dialect: "redis";
    db: number;
    kind: "keyvalue";
    generatedAt: string;
    totalKeys: number;
    namespaces: {
        types: string[];
        pattern: string;
        sampleKeys: string[];
        keyCount: number;
    }[];
}>, z.ZodObject<{
    kind: z.ZodLiteral<"search">;
    dialect: z.ZodEnum<["elasticsearch"]>;
    /** Cluster name as reported by /_cluster/health. */
    cluster: z.ZodOptional<z.ZodString>;
    indices: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        name: z.ZodString;
        /** Approximate doc count from /_stats. */
        docCount: z.ZodOptional<z.ZodNumber>;
        /** Primary shard size bytes. */
        sizeBytes: z.ZodOptional<z.ZodNumber>;
        aliases: z.ZodArray<z.ZodString, "many">;
        fields: z.ZodArray<z.ZodObject<{
            /** Dotted JSON path (e.g. `user.address.city`). */
            name: z.ZodString;
            /** Elasticsearch field type (text/keyword/long/date/object/nested/etc.). */
            type: z.ZodString;
            /** True if field is analyzed text (full-text searchable). */
            analyzed: z.ZodOptional<z.ZodBoolean>;
        }, "strip", z.ZodTypeAny, {
            type: string;
            name: string;
            analyzed?: boolean | undefined;
        }, {
            type: string;
            name: string;
            analyzed?: boolean | undefined;
        }>, "many">;
    }, "strip", z.ZodTypeAny, {
        id: string;
        name: string;
        aliases: string[];
        fields: {
            type: string;
            name: string;
            analyzed?: boolean | undefined;
        }[];
        sizeBytes?: number | undefined;
        docCount?: number | undefined;
    }, {
        id: string;
        name: string;
        aliases: string[];
        fields: {
            type: string;
            name: string;
            analyzed?: boolean | undefined;
        }[];
        sizeBytes?: number | undefined;
        docCount?: number | undefined;
    }>, "many">;
    generatedAt: z.ZodString;
}, "strip", z.ZodTypeAny, {
    dialect: "elasticsearch";
    kind: "search";
    generatedAt: string;
    indices: {
        id: string;
        name: string;
        aliases: string[];
        fields: {
            type: string;
            name: string;
            analyzed?: boolean | undefined;
        }[];
        sizeBytes?: number | undefined;
        docCount?: number | undefined;
    }[];
    cluster?: string | undefined;
}, {
    dialect: "elasticsearch";
    kind: "search";
    generatedAt: string;
    indices: {
        id: string;
        name: string;
        aliases: string[];
        fields: {
            type: string;
            name: string;
            analyzed?: boolean | undefined;
        }[];
        sizeBytes?: number | undefined;
        docCount?: number | undefined;
    }[];
    cluster?: string | undefined;
}>, z.ZodObject<{
    kind: z.ZodLiteral<"document">;
    dialect: z.ZodEnum<["mongodb"]>;
    /** Database the connection points to (default DB from URL). */
    database: z.ZodString;
    collections: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        /** Database name. */
        database: z.ZodString;
        /** Collection name. */
        name: z.ZodString;
        docCount: z.ZodOptional<z.ZodNumber>;
        /** Approximate storage size in bytes. */
        sizeBytes: z.ZodOptional<z.ZodNumber>;
        /** Index names defined on the collection (excluding _id). */
        indexes: z.ZodArray<z.ZodString, "many">;
        fields: z.ZodArray<z.ZodObject<{
            /** Dotted path (e.g. `address.city`). */
            name: z.ZodString;
            /** Detected BSON types across sampled docs. */
            types: z.ZodArray<z.ZodString, "many">;
            /** Fraction of sampled docs containing this field (0..1). */
            presence: z.ZodOptional<z.ZodNumber>;
            /** Sampled values when low cardinality (enum-like). */
            sampleValues: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
        }, "strip", z.ZodTypeAny, {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
            presence?: number | undefined;
        }, {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
            presence?: number | undefined;
        }>, "many">;
    }, "strip", z.ZodTypeAny, {
        id: string;
        database: string;
        name: string;
        fields: {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
            presence?: number | undefined;
        }[];
        indexes: string[];
        sizeBytes?: number | undefined;
        docCount?: number | undefined;
    }, {
        id: string;
        database: string;
        name: string;
        fields: {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
            presence?: number | undefined;
        }[];
        indexes: string[];
        sizeBytes?: number | undefined;
        docCount?: number | undefined;
    }>, "many">;
    generatedAt: z.ZodString;
}, "strip", z.ZodTypeAny, {
    database: string;
    dialect: "mongodb";
    kind: "document";
    generatedAt: string;
    collections: {
        id: string;
        database: string;
        name: string;
        fields: {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
            presence?: number | undefined;
        }[];
        indexes: string[];
        sizeBytes?: number | undefined;
        docCount?: number | undefined;
    }[];
}, {
    database: string;
    dialect: "mongodb";
    kind: "document";
    generatedAt: string;
    collections: {
        id: string;
        database: string;
        name: string;
        fields: {
            name: string;
            types: string[];
            sampleValues?: string[] | undefined;
            presence?: number | undefined;
        }[];
        indexes: string[];
        sizeBytes?: number | undefined;
        docCount?: number | undefined;
    }[];
}>]>;
export type UnifiedSchema = z.infer<typeof UnifiedSchemaSchema>;
//# sourceMappingURL=schema-graph.d.ts.map