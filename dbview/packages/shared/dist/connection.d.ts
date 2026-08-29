import { z } from 'zod';
export declare const SslModeSchema: z.ZodEnum<["disable", "require", "verify-full"]>;
export type SslMode = z.infer<typeof SslModeSchema>;
export declare const PostgresParamsSchema: z.ZodObject<{
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodString;
    username: z.ZodOptional<z.ZodString>;
    password: z.ZodOptional<z.ZodString>;
    sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
} & {
    dialect: z.ZodLiteral<"postgres">;
}, "strip", z.ZodTypeAny, {
    host: string;
    database: string;
    dialect: "postgres";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}, {
    host: string;
    database: string;
    dialect: "postgres";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}>;
export declare const MysqlParamsSchema: z.ZodObject<{
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodString;
    username: z.ZodOptional<z.ZodString>;
    password: z.ZodOptional<z.ZodString>;
    sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
} & {
    dialect: z.ZodLiteral<"mysql">;
}, "strip", z.ZodTypeAny, {
    host: string;
    database: string;
    dialect: "mysql";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}, {
    host: string;
    database: string;
    dialect: "mysql";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}>;
export declare const MariadbParamsSchema: z.ZodObject<{
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodString;
    username: z.ZodOptional<z.ZodString>;
    password: z.ZodOptional<z.ZodString>;
    sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
} & {
    dialect: z.ZodLiteral<"mariadb">;
}, "strip", z.ZodTypeAny, {
    host: string;
    database: string;
    dialect: "mariadb";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}, {
    host: string;
    database: string;
    dialect: "mariadb";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}>;
export declare const MssqlParamsSchema: z.ZodObject<{
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodString;
    username: z.ZodOptional<z.ZodString>;
    password: z.ZodOptional<z.ZodString>;
    sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
} & {
    dialect: z.ZodLiteral<"mssql">;
    encrypt: z.ZodOptional<z.ZodBoolean>;
    trustServerCertificate: z.ZodOptional<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    host: string;
    database: string;
    dialect: "mssql";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    encrypt?: boolean | undefined;
    trustServerCertificate?: boolean | undefined;
}, {
    host: string;
    database: string;
    dialect: "mssql";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    encrypt?: boolean | undefined;
    trustServerCertificate?: boolean | undefined;
}>;
export declare const SqliteParamsSchema: z.ZodObject<{
    dialect: z.ZodLiteral<"sqlite">;
    filePath: z.ZodString;
}, "strip", z.ZodTypeAny, {
    dialect: "sqlite";
    filePath: string;
}, {
    dialect: "sqlite";
    filePath: string;
}>;
export declare const CockroachParamsSchema: z.ZodObject<{
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodString;
    username: z.ZodOptional<z.ZodString>;
    password: z.ZodOptional<z.ZodString>;
    sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
} & {
    dialect: z.ZodLiteral<"cockroach">;
}, "strip", z.ZodTypeAny, {
    host: string;
    database: string;
    dialect: "cockroach";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}, {
    host: string;
    database: string;
    dialect: "cockroach";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}>;
export declare const OracleParamsSchema: z.ZodObject<{
    password: z.ZodOptional<z.ZodString>;
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodOptional<z.ZodString>;
    username: z.ZodOptional<z.ZodString>;
    sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
} & {
    dialect: z.ZodLiteral<"oracle">;
    /** Oracle service name (preferred) or SID. Stored in `database` field for unified URL parsing. */
    serviceName: z.ZodOptional<z.ZodString>;
    sid: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    host: string;
    dialect: "oracle";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    serviceName?: string | undefined;
    sid?: string | undefined;
}, {
    host: string;
    dialect: "oracle";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    serviceName?: string | undefined;
    sid?: string | undefined;
}>;
export declare const ClickhouseParamsSchema: z.ZodObject<{
    password: z.ZodOptional<z.ZodString>;
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodOptional<z.ZodString>;
    username: z.ZodOptional<z.ZodOptional<z.ZodString>>;
    sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
} & {
    dialect: z.ZodLiteral<"clickhouse">;
    /** Use HTTPS interface (port 8443 typically). */
    https: z.ZodOptional<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    host: string;
    dialect: "clickhouse";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    https?: boolean | undefined;
}, {
    host: string;
    dialect: "clickhouse";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    https?: boolean | undefined;
}>;
export declare const DuckdbParamsSchema: z.ZodObject<{
    dialect: z.ZodLiteral<"duckdb">;
    /** Filesystem path to .duckdb file, or `:memory:` for ephemeral. */
    filePath: z.ZodString;
}, "strip", z.ZodTypeAny, {
    dialect: "duckdb";
    filePath: string;
}, {
    dialect: "duckdb";
    filePath: string;
}>;
export declare const MongoParamsSchema: z.ZodObject<{
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodString;
    username: z.ZodOptional<z.ZodString>;
    password: z.ZodOptional<z.ZodString>;
    sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
} & {
    dialect: z.ZodLiteral<"mongodb">;
    authSource: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    host: string;
    database: string;
    dialect: "mongodb";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    authSource?: string | undefined;
}, {
    host: string;
    database: string;
    dialect: "mongodb";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    authSource?: string | undefined;
}>;
export declare const Neo4jParamsSchema: z.ZodObject<{
    password: z.ZodOptional<z.ZodString>;
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    username: z.ZodOptional<z.ZodString>;
    sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
} & {
    dialect: z.ZodLiteral<"neo4j">;
    database: z.ZodOptional<z.ZodString>;
    scheme: z.ZodOptional<z.ZodEnum<["neo4j", "neo4j+s", "bolt", "bolt+s"]>>;
}, "strip", z.ZodTypeAny, {
    host: string;
    dialect: "neo4j";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    scheme?: "neo4j" | "neo4j+s" | "bolt" | "bolt+s" | undefined;
}, {
    host: string;
    dialect: "neo4j";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    scheme?: "neo4j" | "neo4j+s" | "bolt" | "bolt+s" | undefined;
}>;
export declare const FalkorParamsSchema: z.ZodObject<{
    password: z.ZodOptional<z.ZodString>;
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodOptional<z.ZodString>;
    username: z.ZodOptional<z.ZodOptional<z.ZodString>>;
    sslMode: z.ZodOptional<z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>>;
} & {
    dialect: z.ZodLiteral<"falkordb">;
    graph: z.ZodString;
}, "strip", z.ZodTypeAny, {
    graph: string;
    host: string;
    dialect: "falkordb";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}, {
    graph: string;
    host: string;
    dialect: "falkordb";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}>;
export declare const UltipaParamsSchema: z.ZodObject<{
    password: z.ZodOptional<z.ZodString>;
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodOptional<z.ZodString>;
    username: z.ZodOptional<z.ZodString>;
    sslMode: z.ZodOptional<z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>>;
} & {
    dialect: z.ZodLiteral<"ultipa">;
    /** Default graph for the session (server-side `USE GRAPH`). */
    graph: z.ZodOptional<z.ZodString>;
    /** Enable TLS for the gRPC channel. */
    useSSL: z.ZodOptional<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    host: string;
    dialect: "ultipa";
    password?: string | undefined;
    graph?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    useSSL?: boolean | undefined;
}, {
    host: string;
    dialect: "ultipa";
    password?: string | undefined;
    graph?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    useSSL?: boolean | undefined;
}>;
export declare const RedisParamsSchema: z.ZodObject<{
    password: z.ZodOptional<z.ZodString>;
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodOptional<z.ZodString>;
    username: z.ZodOptional<z.ZodOptional<z.ZodString>>;
    sslMode: z.ZodOptional<z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>>;
} & {
    dialect: z.ZodLiteral<"redis">;
    /** Logical DB index (0-15 typical). */
    db: z.ZodOptional<z.ZodNumber>;
    /** Enable TLS. */
    tls: z.ZodOptional<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    host: string;
    dialect: "redis";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    db?: number | undefined;
    tls?: boolean | undefined;
}, {
    host: string;
    dialect: "redis";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    db?: number | undefined;
    tls?: boolean | undefined;
}>;
export declare const ElasticsearchParamsSchema: z.ZodObject<{
    password: z.ZodOptional<z.ZodString>;
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodOptional<z.ZodString>;
    username: z.ZodOptional<z.ZodOptional<z.ZodString>>;
    sslMode: z.ZodOptional<z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>>;
} & {
    dialect: z.ZodLiteral<"elasticsearch">;
    /** Use HTTPS instead of HTTP. */
    https: z.ZodOptional<z.ZodBoolean>;
    /** Optional default index pattern to focus the UI. */
    index: z.ZodOptional<z.ZodString>;
    /** API key for ES Cloud or 8.x token-based auth. */
    apiKey: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    host: string;
    dialect: "elasticsearch";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    https?: boolean | undefined;
    index?: string | undefined;
    apiKey?: string | undefined;
}, {
    host: string;
    dialect: "elasticsearch";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    https?: boolean | undefined;
    index?: string | undefined;
    apiKey?: string | undefined;
}>;
export declare const QdrantParamsSchema: z.ZodObject<{
    dialect: z.ZodLiteral<"qdrant">;
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    /** TLS via https. Default false (plain HTTP for local). */
    https: z.ZodOptional<z.ZodBoolean>;
    /** API key sent as `api-key` header. Optional for local dev. */
    apiKey: z.ZodOptional<z.ZodString>;
    /** Optional default collection to focus the UI on. */
    collection: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    host: string;
    dialect: "qdrant";
    port?: number | undefined;
    https?: boolean | undefined;
    apiKey?: string | undefined;
    collection?: string | undefined;
}, {
    host: string;
    dialect: "qdrant";
    port?: number | undefined;
    https?: boolean | undefined;
    apiKey?: string | undefined;
    collection?: string | undefined;
}>;
/**
 * Salesforce connection params. Authentication: OAuth 2.0 Client Credentials Flow only
 * (Connected App with "Enable Client Credentials Flow" + a "Run As" user).
 * Username-Password is deprecated by Salesforce; JWT Bearer is not yet implemented here.
 */
export declare const SalesforceParamsSchema: z.ZodObject<{
    dialect: z.ZodLiteral<"salesforce">;
    /** Full instance URL, e.g. `https://acme.my.salesforce.com` (no trailing slash). */
    instanceUrl: z.ZodString;
    /** Salesforce REST API version, e.g. `v60.0`. Default `v60.0`. */
    apiVersion: z.ZodOptional<z.ZodString>;
    /** Connected App consumer key. */
    clientId: z.ZodString;
    /** Connected App consumer secret (encrypted at rest). */
    clientSecret: z.ZodString;
    /** Sandbox flag — informational; Client Credentials uses instanceUrl directly. */
    isSandbox: z.ZodOptional<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    dialect: "salesforce";
    instanceUrl: string;
    clientId: string;
    clientSecret: string;
    apiVersion?: string | undefined;
    isSandbox?: boolean | undefined;
}, {
    dialect: "salesforce";
    instanceUrl: string;
    clientId: string;
    clientSecret: string;
    apiVersion?: string | undefined;
    isSandbox?: boolean | undefined;
}>;
/**
 * Salesforce Data Cloud connection params.
 *
 * Authentication: OAuth 2.0 Client Credentials Flow (MVP). The Connected App
 * must enable Client Credentials + Data Cloud scopes (`cdp_query_api`,
 * `cdp_profile_api`, `cdp_ingest_api`, `cdp_calculated_insight_api`, `cdp_api`).
 * After obtaining a Core access token, the client performs a token exchange
 * against `/services/a360/token` to receive a Data-Cloud-scoped CDP token
 * + the tenant URL used for `/api/v2/query` calls.
 *
 * JWT Bearer flow is intentionally not implemented in the MVP; the schema is
 * shaped so it can be added without breaking changes (extra optional fields).
 */
export declare const SalesforceDataCloudParamsSchema: z.ZodObject<{
    dialect: z.ZodLiteral<"salesforce-data-cloud">;
    /** Core login / My Domain URL, e.g. `https://acme.my.salesforce.com`. */
    loginUrl: z.ZodString;
    /** Salesforce Data Cloud REST API version path segment, default `v60.0`. */
    apiVersion: z.ZodOptional<z.ZodString>;
    /** Connected App consumer key (client_id). */
    clientId: z.ZodString;
    /** Connected App consumer secret (client_secret). Encrypted at rest. */
    clientSecret: z.ZodString;
    /**
     * Optional dataspace. Data Cloud orgs default to `default`; when an org
     * defines multiple dataspaces (brand-level data isolation) callers may pick
     * one. Currently informational — query endpoint resolves it via auth scope.
     */
    dataspace: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    dialect: "salesforce-data-cloud";
    clientId: string;
    clientSecret: string;
    loginUrl: string;
    apiVersion?: string | undefined;
    dataspace?: string | undefined;
}, {
    dialect: "salesforce-data-cloud";
    clientId: string;
    clientSecret: string;
    loginUrl: string;
    apiVersion?: string | undefined;
    dataspace?: string | undefined;
}>;
export declare const ConnectionParamsSchema: z.ZodDiscriminatedUnion<"dialect", [z.ZodObject<{
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodString;
    username: z.ZodOptional<z.ZodString>;
    password: z.ZodOptional<z.ZodString>;
    sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
} & {
    dialect: z.ZodLiteral<"postgres">;
}, "strip", z.ZodTypeAny, {
    host: string;
    database: string;
    dialect: "postgres";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}, {
    host: string;
    database: string;
    dialect: "postgres";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}>, z.ZodObject<{
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodString;
    username: z.ZodOptional<z.ZodString>;
    password: z.ZodOptional<z.ZodString>;
    sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
} & {
    dialect: z.ZodLiteral<"mysql">;
}, "strip", z.ZodTypeAny, {
    host: string;
    database: string;
    dialect: "mysql";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}, {
    host: string;
    database: string;
    dialect: "mysql";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}>, z.ZodObject<{
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodString;
    username: z.ZodOptional<z.ZodString>;
    password: z.ZodOptional<z.ZodString>;
    sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
} & {
    dialect: z.ZodLiteral<"mariadb">;
}, "strip", z.ZodTypeAny, {
    host: string;
    database: string;
    dialect: "mariadb";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}, {
    host: string;
    database: string;
    dialect: "mariadb";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}>, z.ZodObject<{
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodString;
    username: z.ZodOptional<z.ZodString>;
    password: z.ZodOptional<z.ZodString>;
    sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
} & {
    dialect: z.ZodLiteral<"mssql">;
    encrypt: z.ZodOptional<z.ZodBoolean>;
    trustServerCertificate: z.ZodOptional<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    host: string;
    database: string;
    dialect: "mssql";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    encrypt?: boolean | undefined;
    trustServerCertificate?: boolean | undefined;
}, {
    host: string;
    database: string;
    dialect: "mssql";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    encrypt?: boolean | undefined;
    trustServerCertificate?: boolean | undefined;
}>, z.ZodObject<{
    dialect: z.ZodLiteral<"sqlite">;
    filePath: z.ZodString;
}, "strip", z.ZodTypeAny, {
    dialect: "sqlite";
    filePath: string;
}, {
    dialect: "sqlite";
    filePath: string;
}>, z.ZodObject<{
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodString;
    username: z.ZodOptional<z.ZodString>;
    password: z.ZodOptional<z.ZodString>;
    sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
} & {
    dialect: z.ZodLiteral<"cockroach">;
}, "strip", z.ZodTypeAny, {
    host: string;
    database: string;
    dialect: "cockroach";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}, {
    host: string;
    database: string;
    dialect: "cockroach";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}>, z.ZodObject<{
    password: z.ZodOptional<z.ZodString>;
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodOptional<z.ZodString>;
    username: z.ZodOptional<z.ZodString>;
    sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
} & {
    dialect: z.ZodLiteral<"oracle">;
    /** Oracle service name (preferred) or SID. Stored in `database` field for unified URL parsing. */
    serviceName: z.ZodOptional<z.ZodString>;
    sid: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    host: string;
    dialect: "oracle";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    serviceName?: string | undefined;
    sid?: string | undefined;
}, {
    host: string;
    dialect: "oracle";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    serviceName?: string | undefined;
    sid?: string | undefined;
}>, z.ZodObject<{
    password: z.ZodOptional<z.ZodString>;
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodOptional<z.ZodString>;
    username: z.ZodOptional<z.ZodOptional<z.ZodString>>;
    sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
} & {
    dialect: z.ZodLiteral<"clickhouse">;
    /** Use HTTPS interface (port 8443 typically). */
    https: z.ZodOptional<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    host: string;
    dialect: "clickhouse";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    https?: boolean | undefined;
}, {
    host: string;
    dialect: "clickhouse";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    https?: boolean | undefined;
}>, z.ZodObject<{
    dialect: z.ZodLiteral<"duckdb">;
    /** Filesystem path to .duckdb file, or `:memory:` for ephemeral. */
    filePath: z.ZodString;
}, "strip", z.ZodTypeAny, {
    dialect: "duckdb";
    filePath: string;
}, {
    dialect: "duckdb";
    filePath: string;
}>, z.ZodObject<{
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodString;
    username: z.ZodOptional<z.ZodString>;
    password: z.ZodOptional<z.ZodString>;
    sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
} & {
    dialect: z.ZodLiteral<"mongodb">;
    authSource: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    host: string;
    database: string;
    dialect: "mongodb";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    authSource?: string | undefined;
}, {
    host: string;
    database: string;
    dialect: "mongodb";
    password?: string | undefined;
    port?: number | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    authSource?: string | undefined;
}>, z.ZodObject<{
    password: z.ZodOptional<z.ZodString>;
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    username: z.ZodOptional<z.ZodString>;
    sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
} & {
    dialect: z.ZodLiteral<"neo4j">;
    database: z.ZodOptional<z.ZodString>;
    scheme: z.ZodOptional<z.ZodEnum<["neo4j", "neo4j+s", "bolt", "bolt+s"]>>;
}, "strip", z.ZodTypeAny, {
    host: string;
    dialect: "neo4j";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    scheme?: "neo4j" | "neo4j+s" | "bolt" | "bolt+s" | undefined;
}, {
    host: string;
    dialect: "neo4j";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    scheme?: "neo4j" | "neo4j+s" | "bolt" | "bolt+s" | undefined;
}>, z.ZodObject<{
    password: z.ZodOptional<z.ZodString>;
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodOptional<z.ZodString>;
    username: z.ZodOptional<z.ZodOptional<z.ZodString>>;
    sslMode: z.ZodOptional<z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>>;
} & {
    dialect: z.ZodLiteral<"falkordb">;
    graph: z.ZodString;
}, "strip", z.ZodTypeAny, {
    graph: string;
    host: string;
    dialect: "falkordb";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}, {
    graph: string;
    host: string;
    dialect: "falkordb";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
}>, z.ZodObject<{
    password: z.ZodOptional<z.ZodString>;
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodOptional<z.ZodString>;
    username: z.ZodOptional<z.ZodString>;
    sslMode: z.ZodOptional<z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>>;
} & {
    dialect: z.ZodLiteral<"ultipa">;
    /** Default graph for the session (server-side `USE GRAPH`). */
    graph: z.ZodOptional<z.ZodString>;
    /** Enable TLS for the gRPC channel. */
    useSSL: z.ZodOptional<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    host: string;
    dialect: "ultipa";
    password?: string | undefined;
    graph?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    useSSL?: boolean | undefined;
}, {
    host: string;
    dialect: "ultipa";
    password?: string | undefined;
    graph?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    useSSL?: boolean | undefined;
}>, z.ZodObject<{
    dialect: z.ZodLiteral<"qdrant">;
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    /** TLS via https. Default false (plain HTTP for local). */
    https: z.ZodOptional<z.ZodBoolean>;
    /** API key sent as `api-key` header. Optional for local dev. */
    apiKey: z.ZodOptional<z.ZodString>;
    /** Optional default collection to focus the UI on. */
    collection: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    host: string;
    dialect: "qdrant";
    port?: number | undefined;
    https?: boolean | undefined;
    apiKey?: string | undefined;
    collection?: string | undefined;
}, {
    host: string;
    dialect: "qdrant";
    port?: number | undefined;
    https?: boolean | undefined;
    apiKey?: string | undefined;
    collection?: string | undefined;
}>, z.ZodObject<{
    password: z.ZodOptional<z.ZodString>;
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodOptional<z.ZodString>;
    username: z.ZodOptional<z.ZodOptional<z.ZodString>>;
    sslMode: z.ZodOptional<z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>>;
} & {
    dialect: z.ZodLiteral<"redis">;
    /** Logical DB index (0-15 typical). */
    db: z.ZodOptional<z.ZodNumber>;
    /** Enable TLS. */
    tls: z.ZodOptional<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    host: string;
    dialect: "redis";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    db?: number | undefined;
    tls?: boolean | undefined;
}, {
    host: string;
    dialect: "redis";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    db?: number | undefined;
    tls?: boolean | undefined;
}>, z.ZodObject<{
    password: z.ZodOptional<z.ZodString>;
    host: z.ZodString;
    port: z.ZodOptional<z.ZodNumber>;
    database: z.ZodOptional<z.ZodString>;
    username: z.ZodOptional<z.ZodOptional<z.ZodString>>;
    sslMode: z.ZodOptional<z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>>;
} & {
    dialect: z.ZodLiteral<"elasticsearch">;
    /** Use HTTPS instead of HTTP. */
    https: z.ZodOptional<z.ZodBoolean>;
    /** Optional default index pattern to focus the UI. */
    index: z.ZodOptional<z.ZodString>;
    /** API key for ES Cloud or 8.x token-based auth. */
    apiKey: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    host: string;
    dialect: "elasticsearch";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    https?: boolean | undefined;
    index?: string | undefined;
    apiKey?: string | undefined;
}, {
    host: string;
    dialect: "elasticsearch";
    password?: string | undefined;
    port?: number | undefined;
    database?: string | undefined;
    username?: string | undefined;
    sslMode?: "disable" | "require" | "verify-full" | undefined;
    https?: boolean | undefined;
    index?: string | undefined;
    apiKey?: string | undefined;
}>, z.ZodObject<{
    dialect: z.ZodLiteral<"salesforce">;
    /** Full instance URL, e.g. `https://acme.my.salesforce.com` (no trailing slash). */
    instanceUrl: z.ZodString;
    /** Salesforce REST API version, e.g. `v60.0`. Default `v60.0`. */
    apiVersion: z.ZodOptional<z.ZodString>;
    /** Connected App consumer key. */
    clientId: z.ZodString;
    /** Connected App consumer secret (encrypted at rest). */
    clientSecret: z.ZodString;
    /** Sandbox flag — informational; Client Credentials uses instanceUrl directly. */
    isSandbox: z.ZodOptional<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    dialect: "salesforce";
    instanceUrl: string;
    clientId: string;
    clientSecret: string;
    apiVersion?: string | undefined;
    isSandbox?: boolean | undefined;
}, {
    dialect: "salesforce";
    instanceUrl: string;
    clientId: string;
    clientSecret: string;
    apiVersion?: string | undefined;
    isSandbox?: boolean | undefined;
}>, z.ZodObject<{
    dialect: z.ZodLiteral<"salesforce-data-cloud">;
    /** Core login / My Domain URL, e.g. `https://acme.my.salesforce.com`. */
    loginUrl: z.ZodString;
    /** Salesforce Data Cloud REST API version path segment, default `v60.0`. */
    apiVersion: z.ZodOptional<z.ZodString>;
    /** Connected App consumer key (client_id). */
    clientId: z.ZodString;
    /** Connected App consumer secret (client_secret). Encrypted at rest. */
    clientSecret: z.ZodString;
    /**
     * Optional dataspace. Data Cloud orgs default to `default`; when an org
     * defines multiple dataspaces (brand-level data isolation) callers may pick
     * one. Currently informational — query endpoint resolves it via auth scope.
     */
    dataspace: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    dialect: "salesforce-data-cloud";
    clientId: string;
    clientSecret: string;
    loginUrl: string;
    apiVersion?: string | undefined;
    dataspace?: string | undefined;
}, {
    dialect: "salesforce-data-cloud";
    clientId: string;
    clientSecret: string;
    loginUrl: string;
    apiVersion?: string | undefined;
    dataspace?: string | undefined;
}>]>;
export type ConnectionParams = z.infer<typeof ConnectionParamsSchema>;
/**
 * Sharing policy attached to every connection. Connections are owned by an
 * admin (the only role allowed to create them). `mode` controls visibility:
 *
 * - `private` — only the owner sees it (other admins are *not* implicitly
 *               granted access; this is true ownership privacy).
 * - `admins`  — every admin sees it; non-admin users do not.
 * - `all`     — every authenticated user sees it.
 * - `users`   — listed userIds plus the owner see it. Other admins do NOT
 *               see it unless they own it (use `admins` for admin-wide).
 *
 * Defaults: new connections are `private`. The v1→v2 store migration upgrades
 * pre-existing `private` entries to `admins` so installations with multiple
 * admins do not lose access on upgrade.
 */
export declare const ConnectionSharingSchema: z.ZodEffects<z.ZodObject<{
    mode: z.ZodEnum<["private", "admins", "all", "users"]>;
    userIds: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
}, "strip", z.ZodTypeAny, {
    mode: "private" | "admins" | "all" | "users";
    userIds: string[];
}, {
    mode: "private" | "admins" | "all" | "users";
    userIds?: string[] | undefined;
}>, {
    mode: "private" | "admins" | "all" | "users";
    userIds: string[];
}, {
    mode: "private" | "admins" | "all" | "users";
    userIds?: string[] | undefined;
}>;
export type ConnectionSharing = z.infer<typeof ConnectionSharingSchema>;
export declare const ConnectionConfigSchema: z.ZodObject<{
    id: z.ZodString;
    name: z.ZodString;
    dialect: z.ZodEnum<["postgres", "mysql", "mariadb", "mssql", "sqlite", "cockroach", "oracle", "clickhouse", "duckdb", "mongodb", "neo4j", "falkordb", "ultipa", "qdrant", "redis", "elasticsearch", "salesforce", "salesforce-data-cloud"]>;
    connectionStringCipher: z.ZodOptional<z.ZodString>;
    /**
     * Encrypted JSON of the structured `ConnectionParams` the admin originally
     * supplied at create time. Used to re-pre-fill the edit dialog with the
     * non-secret fields (host, port, db, user...) without ever shipping the
     * decrypted secrets over HTTP. Absent for connections created from a raw
     * URL or imported via legacy paths.
     */
    paramsCipher: z.ZodOptional<z.ZodString>;
    displayHost: z.ZodOptional<z.ZodString>;
    displayDatabase: z.ZodOptional<z.ZodString>;
    readOnly: z.ZodDefault<z.ZodLiteral<true>>;
    ownerId: z.ZodString;
    sharing: z.ZodEffects<z.ZodObject<{
        mode: z.ZodEnum<["private", "admins", "all", "users"]>;
        userIds: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
    }, "strip", z.ZodTypeAny, {
        mode: "private" | "admins" | "all" | "users";
        userIds: string[];
    }, {
        mode: "private" | "admins" | "all" | "users";
        userIds?: string[] | undefined;
    }>, {
        mode: "private" | "admins" | "all" | "users";
        userIds: string[];
    }, {
        mode: "private" | "admins" | "all" | "users";
        userIds?: string[] | undefined;
    }>;
    createdAt: z.ZodString;
}, "strip", z.ZodTypeAny, {
    id: string;
    createdAt: string;
    dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "neo4j" | "falkordb" | "ultipa" | "mongodb" | "qdrant" | "redis" | "elasticsearch" | "salesforce" | "salesforce-data-cloud";
    name: string;
    readOnly: true;
    ownerId: string;
    sharing: {
        mode: "private" | "admins" | "all" | "users";
        userIds: string[];
    };
    connectionStringCipher?: string | undefined;
    paramsCipher?: string | undefined;
    displayHost?: string | undefined;
    displayDatabase?: string | undefined;
}, {
    id: string;
    createdAt: string;
    dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "neo4j" | "falkordb" | "ultipa" | "mongodb" | "qdrant" | "redis" | "elasticsearch" | "salesforce" | "salesforce-data-cloud";
    name: string;
    ownerId: string;
    sharing: {
        mode: "private" | "admins" | "all" | "users";
        userIds?: string[] | undefined;
    };
    connectionStringCipher?: string | undefined;
    paramsCipher?: string | undefined;
    displayHost?: string | undefined;
    displayDatabase?: string | undefined;
    readOnly?: true | undefined;
}>;
export type ConnectionConfig = z.infer<typeof ConnectionConfigSchema>;
export declare const CreateConnectionSchema: z.ZodEffects<z.ZodEffects<z.ZodObject<{
    name: z.ZodString;
    dialect: z.ZodEnum<["postgres", "mysql", "mariadb", "mssql", "sqlite", "cockroach", "oracle", "clickhouse", "duckdb", "mongodb", "neo4j", "falkordb", "ultipa", "qdrant", "redis", "elasticsearch", "salesforce", "salesforce-data-cloud"]>;
    params: z.ZodOptional<z.ZodDiscriminatedUnion<"dialect", [z.ZodObject<{
        host: z.ZodString;
        port: z.ZodOptional<z.ZodNumber>;
        database: z.ZodString;
        username: z.ZodOptional<z.ZodString>;
        password: z.ZodOptional<z.ZodString>;
        sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
    } & {
        dialect: z.ZodLiteral<"postgres">;
    }, "strip", z.ZodTypeAny, {
        host: string;
        database: string;
        dialect: "postgres";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    }, {
        host: string;
        database: string;
        dialect: "postgres";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    }>, z.ZodObject<{
        host: z.ZodString;
        port: z.ZodOptional<z.ZodNumber>;
        database: z.ZodString;
        username: z.ZodOptional<z.ZodString>;
        password: z.ZodOptional<z.ZodString>;
        sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
    } & {
        dialect: z.ZodLiteral<"mysql">;
    }, "strip", z.ZodTypeAny, {
        host: string;
        database: string;
        dialect: "mysql";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    }, {
        host: string;
        database: string;
        dialect: "mysql";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    }>, z.ZodObject<{
        host: z.ZodString;
        port: z.ZodOptional<z.ZodNumber>;
        database: z.ZodString;
        username: z.ZodOptional<z.ZodString>;
        password: z.ZodOptional<z.ZodString>;
        sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
    } & {
        dialect: z.ZodLiteral<"mariadb">;
    }, "strip", z.ZodTypeAny, {
        host: string;
        database: string;
        dialect: "mariadb";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    }, {
        host: string;
        database: string;
        dialect: "mariadb";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    }>, z.ZodObject<{
        host: z.ZodString;
        port: z.ZodOptional<z.ZodNumber>;
        database: z.ZodString;
        username: z.ZodOptional<z.ZodString>;
        password: z.ZodOptional<z.ZodString>;
        sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
    } & {
        dialect: z.ZodLiteral<"mssql">;
        encrypt: z.ZodOptional<z.ZodBoolean>;
        trustServerCertificate: z.ZodOptional<z.ZodBoolean>;
    }, "strip", z.ZodTypeAny, {
        host: string;
        database: string;
        dialect: "mssql";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        encrypt?: boolean | undefined;
        trustServerCertificate?: boolean | undefined;
    }, {
        host: string;
        database: string;
        dialect: "mssql";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        encrypt?: boolean | undefined;
        trustServerCertificate?: boolean | undefined;
    }>, z.ZodObject<{
        dialect: z.ZodLiteral<"sqlite">;
        filePath: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        dialect: "sqlite";
        filePath: string;
    }, {
        dialect: "sqlite";
        filePath: string;
    }>, z.ZodObject<{
        host: z.ZodString;
        port: z.ZodOptional<z.ZodNumber>;
        database: z.ZodString;
        username: z.ZodOptional<z.ZodString>;
        password: z.ZodOptional<z.ZodString>;
        sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
    } & {
        dialect: z.ZodLiteral<"cockroach">;
    }, "strip", z.ZodTypeAny, {
        host: string;
        database: string;
        dialect: "cockroach";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    }, {
        host: string;
        database: string;
        dialect: "cockroach";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    }>, z.ZodObject<{
        password: z.ZodOptional<z.ZodString>;
        host: z.ZodString;
        port: z.ZodOptional<z.ZodNumber>;
        database: z.ZodOptional<z.ZodString>;
        username: z.ZodOptional<z.ZodString>;
        sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
    } & {
        dialect: z.ZodLiteral<"oracle">;
        /** Oracle service name (preferred) or SID. Stored in `database` field for unified URL parsing. */
        serviceName: z.ZodOptional<z.ZodString>;
        sid: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        host: string;
        dialect: "oracle";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        serviceName?: string | undefined;
        sid?: string | undefined;
    }, {
        host: string;
        dialect: "oracle";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        serviceName?: string | undefined;
        sid?: string | undefined;
    }>, z.ZodObject<{
        password: z.ZodOptional<z.ZodString>;
        host: z.ZodString;
        port: z.ZodOptional<z.ZodNumber>;
        database: z.ZodOptional<z.ZodString>;
        username: z.ZodOptional<z.ZodOptional<z.ZodString>>;
        sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
    } & {
        dialect: z.ZodLiteral<"clickhouse">;
        /** Use HTTPS interface (port 8443 typically). */
        https: z.ZodOptional<z.ZodBoolean>;
    }, "strip", z.ZodTypeAny, {
        host: string;
        dialect: "clickhouse";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        https?: boolean | undefined;
    }, {
        host: string;
        dialect: "clickhouse";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        https?: boolean | undefined;
    }>, z.ZodObject<{
        dialect: z.ZodLiteral<"duckdb">;
        /** Filesystem path to .duckdb file, or `:memory:` for ephemeral. */
        filePath: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        dialect: "duckdb";
        filePath: string;
    }, {
        dialect: "duckdb";
        filePath: string;
    }>, z.ZodObject<{
        host: z.ZodString;
        port: z.ZodOptional<z.ZodNumber>;
        database: z.ZodString;
        username: z.ZodOptional<z.ZodString>;
        password: z.ZodOptional<z.ZodString>;
        sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
    } & {
        dialect: z.ZodLiteral<"mongodb">;
        authSource: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        host: string;
        database: string;
        dialect: "mongodb";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        authSource?: string | undefined;
    }, {
        host: string;
        database: string;
        dialect: "mongodb";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        authSource?: string | undefined;
    }>, z.ZodObject<{
        password: z.ZodOptional<z.ZodString>;
        host: z.ZodString;
        port: z.ZodOptional<z.ZodNumber>;
        username: z.ZodOptional<z.ZodString>;
        sslMode: z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>;
    } & {
        dialect: z.ZodLiteral<"neo4j">;
        database: z.ZodOptional<z.ZodString>;
        scheme: z.ZodOptional<z.ZodEnum<["neo4j", "neo4j+s", "bolt", "bolt+s"]>>;
    }, "strip", z.ZodTypeAny, {
        host: string;
        dialect: "neo4j";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        scheme?: "neo4j" | "neo4j+s" | "bolt" | "bolt+s" | undefined;
    }, {
        host: string;
        dialect: "neo4j";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        scheme?: "neo4j" | "neo4j+s" | "bolt" | "bolt+s" | undefined;
    }>, z.ZodObject<{
        password: z.ZodOptional<z.ZodString>;
        host: z.ZodString;
        port: z.ZodOptional<z.ZodNumber>;
        database: z.ZodOptional<z.ZodString>;
        username: z.ZodOptional<z.ZodOptional<z.ZodString>>;
        sslMode: z.ZodOptional<z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>>;
    } & {
        dialect: z.ZodLiteral<"falkordb">;
        graph: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        graph: string;
        host: string;
        dialect: "falkordb";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    }, {
        graph: string;
        host: string;
        dialect: "falkordb";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    }>, z.ZodObject<{
        password: z.ZodOptional<z.ZodString>;
        host: z.ZodString;
        port: z.ZodOptional<z.ZodNumber>;
        database: z.ZodOptional<z.ZodString>;
        username: z.ZodOptional<z.ZodString>;
        sslMode: z.ZodOptional<z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>>;
    } & {
        dialect: z.ZodLiteral<"ultipa">;
        /** Default graph for the session (server-side `USE GRAPH`). */
        graph: z.ZodOptional<z.ZodString>;
        /** Enable TLS for the gRPC channel. */
        useSSL: z.ZodOptional<z.ZodBoolean>;
    }, "strip", z.ZodTypeAny, {
        host: string;
        dialect: "ultipa";
        password?: string | undefined;
        graph?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        useSSL?: boolean | undefined;
    }, {
        host: string;
        dialect: "ultipa";
        password?: string | undefined;
        graph?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        useSSL?: boolean | undefined;
    }>, z.ZodObject<{
        dialect: z.ZodLiteral<"qdrant">;
        host: z.ZodString;
        port: z.ZodOptional<z.ZodNumber>;
        /** TLS via https. Default false (plain HTTP for local). */
        https: z.ZodOptional<z.ZodBoolean>;
        /** API key sent as `api-key` header. Optional for local dev. */
        apiKey: z.ZodOptional<z.ZodString>;
        /** Optional default collection to focus the UI on. */
        collection: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        host: string;
        dialect: "qdrant";
        port?: number | undefined;
        https?: boolean | undefined;
        apiKey?: string | undefined;
        collection?: string | undefined;
    }, {
        host: string;
        dialect: "qdrant";
        port?: number | undefined;
        https?: boolean | undefined;
        apiKey?: string | undefined;
        collection?: string | undefined;
    }>, z.ZodObject<{
        password: z.ZodOptional<z.ZodString>;
        host: z.ZodString;
        port: z.ZodOptional<z.ZodNumber>;
        database: z.ZodOptional<z.ZodString>;
        username: z.ZodOptional<z.ZodOptional<z.ZodString>>;
        sslMode: z.ZodOptional<z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>>;
    } & {
        dialect: z.ZodLiteral<"redis">;
        /** Logical DB index (0-15 typical). */
        db: z.ZodOptional<z.ZodNumber>;
        /** Enable TLS. */
        tls: z.ZodOptional<z.ZodBoolean>;
    }, "strip", z.ZodTypeAny, {
        host: string;
        dialect: "redis";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        db?: number | undefined;
        tls?: boolean | undefined;
    }, {
        host: string;
        dialect: "redis";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        db?: number | undefined;
        tls?: boolean | undefined;
    }>, z.ZodObject<{
        password: z.ZodOptional<z.ZodString>;
        host: z.ZodString;
        port: z.ZodOptional<z.ZodNumber>;
        database: z.ZodOptional<z.ZodString>;
        username: z.ZodOptional<z.ZodOptional<z.ZodString>>;
        sslMode: z.ZodOptional<z.ZodOptional<z.ZodEnum<["disable", "require", "verify-full"]>>>;
    } & {
        dialect: z.ZodLiteral<"elasticsearch">;
        /** Use HTTPS instead of HTTP. */
        https: z.ZodOptional<z.ZodBoolean>;
        /** Optional default index pattern to focus the UI. */
        index: z.ZodOptional<z.ZodString>;
        /** API key for ES Cloud or 8.x token-based auth. */
        apiKey: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        host: string;
        dialect: "elasticsearch";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        https?: boolean | undefined;
        index?: string | undefined;
        apiKey?: string | undefined;
    }, {
        host: string;
        dialect: "elasticsearch";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        https?: boolean | undefined;
        index?: string | undefined;
        apiKey?: string | undefined;
    }>, z.ZodObject<{
        dialect: z.ZodLiteral<"salesforce">;
        /** Full instance URL, e.g. `https://acme.my.salesforce.com` (no trailing slash). */
        instanceUrl: z.ZodString;
        /** Salesforce REST API version, e.g. `v60.0`. Default `v60.0`. */
        apiVersion: z.ZodOptional<z.ZodString>;
        /** Connected App consumer key. */
        clientId: z.ZodString;
        /** Connected App consumer secret (encrypted at rest). */
        clientSecret: z.ZodString;
        /** Sandbox flag — informational; Client Credentials uses instanceUrl directly. */
        isSandbox: z.ZodOptional<z.ZodBoolean>;
    }, "strip", z.ZodTypeAny, {
        dialect: "salesforce";
        instanceUrl: string;
        clientId: string;
        clientSecret: string;
        apiVersion?: string | undefined;
        isSandbox?: boolean | undefined;
    }, {
        dialect: "salesforce";
        instanceUrl: string;
        clientId: string;
        clientSecret: string;
        apiVersion?: string | undefined;
        isSandbox?: boolean | undefined;
    }>, z.ZodObject<{
        dialect: z.ZodLiteral<"salesforce-data-cloud">;
        /** Core login / My Domain URL, e.g. `https://acme.my.salesforce.com`. */
        loginUrl: z.ZodString;
        /** Salesforce Data Cloud REST API version path segment, default `v60.0`. */
        apiVersion: z.ZodOptional<z.ZodString>;
        /** Connected App consumer key (client_id). */
        clientId: z.ZodString;
        /** Connected App consumer secret (client_secret). Encrypted at rest. */
        clientSecret: z.ZodString;
        /**
         * Optional dataspace. Data Cloud orgs default to `default`; when an org
         * defines multiple dataspaces (brand-level data isolation) callers may pick
         * one. Currently informational — query endpoint resolves it via auth scope.
         */
        dataspace: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        dialect: "salesforce-data-cloud";
        clientId: string;
        clientSecret: string;
        loginUrl: string;
        apiVersion?: string | undefined;
        dataspace?: string | undefined;
    }, {
        dialect: "salesforce-data-cloud";
        clientId: string;
        clientSecret: string;
        loginUrl: string;
        apiVersion?: string | undefined;
        dataspace?: string | undefined;
    }>]>>;
    connectionString: z.ZodOptional<z.ZodString>;
    sharing: z.ZodOptional<z.ZodEffects<z.ZodObject<{
        mode: z.ZodEnum<["private", "admins", "all", "users"]>;
        userIds: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
    }, "strip", z.ZodTypeAny, {
        mode: "private" | "admins" | "all" | "users";
        userIds: string[];
    }, {
        mode: "private" | "admins" | "all" | "users";
        userIds?: string[] | undefined;
    }>, {
        mode: "private" | "admins" | "all" | "users";
        userIds: string[];
    }, {
        mode: "private" | "admins" | "all" | "users";
        userIds?: string[] | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "neo4j" | "falkordb" | "ultipa" | "mongodb" | "qdrant" | "redis" | "elasticsearch" | "salesforce" | "salesforce-data-cloud";
    name: string;
    params?: {
        host: string;
        database: string;
        dialect: "postgres";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        database: string;
        dialect: "mysql";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        database: string;
        dialect: "mariadb";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        database: string;
        dialect: "mssql";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        encrypt?: boolean | undefined;
        trustServerCertificate?: boolean | undefined;
    } | {
        dialect: "sqlite";
        filePath: string;
    } | {
        host: string;
        database: string;
        dialect: "cockroach";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        dialect: "oracle";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        serviceName?: string | undefined;
        sid?: string | undefined;
    } | {
        host: string;
        dialect: "clickhouse";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        https?: boolean | undefined;
    } | {
        dialect: "duckdb";
        filePath: string;
    } | {
        host: string;
        database: string;
        dialect: "mongodb";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        authSource?: string | undefined;
    } | {
        host: string;
        dialect: "neo4j";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        scheme?: "neo4j" | "neo4j+s" | "bolt" | "bolt+s" | undefined;
    } | {
        graph: string;
        host: string;
        dialect: "falkordb";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        dialect: "ultipa";
        password?: string | undefined;
        graph?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        useSSL?: boolean | undefined;
    } | {
        host: string;
        dialect: "redis";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        db?: number | undefined;
        tls?: boolean | undefined;
    } | {
        host: string;
        dialect: "elasticsearch";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        https?: boolean | undefined;
        index?: string | undefined;
        apiKey?: string | undefined;
    } | {
        host: string;
        dialect: "qdrant";
        port?: number | undefined;
        https?: boolean | undefined;
        apiKey?: string | undefined;
        collection?: string | undefined;
    } | {
        dialect: "salesforce";
        instanceUrl: string;
        clientId: string;
        clientSecret: string;
        apiVersion?: string | undefined;
        isSandbox?: boolean | undefined;
    } | {
        dialect: "salesforce-data-cloud";
        clientId: string;
        clientSecret: string;
        loginUrl: string;
        apiVersion?: string | undefined;
        dataspace?: string | undefined;
    } | undefined;
    sharing?: {
        mode: "private" | "admins" | "all" | "users";
        userIds: string[];
    } | undefined;
    connectionString?: string | undefined;
}, {
    dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "neo4j" | "falkordb" | "ultipa" | "mongodb" | "qdrant" | "redis" | "elasticsearch" | "salesforce" | "salesforce-data-cloud";
    name: string;
    params?: {
        host: string;
        database: string;
        dialect: "postgres";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        database: string;
        dialect: "mysql";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        database: string;
        dialect: "mariadb";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        database: string;
        dialect: "mssql";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        encrypt?: boolean | undefined;
        trustServerCertificate?: boolean | undefined;
    } | {
        dialect: "sqlite";
        filePath: string;
    } | {
        host: string;
        database: string;
        dialect: "cockroach";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        dialect: "oracle";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        serviceName?: string | undefined;
        sid?: string | undefined;
    } | {
        host: string;
        dialect: "clickhouse";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        https?: boolean | undefined;
    } | {
        dialect: "duckdb";
        filePath: string;
    } | {
        host: string;
        database: string;
        dialect: "mongodb";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        authSource?: string | undefined;
    } | {
        host: string;
        dialect: "neo4j";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        scheme?: "neo4j" | "neo4j+s" | "bolt" | "bolt+s" | undefined;
    } | {
        graph: string;
        host: string;
        dialect: "falkordb";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        dialect: "ultipa";
        password?: string | undefined;
        graph?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        useSSL?: boolean | undefined;
    } | {
        host: string;
        dialect: "redis";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        db?: number | undefined;
        tls?: boolean | undefined;
    } | {
        host: string;
        dialect: "elasticsearch";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        https?: boolean | undefined;
        index?: string | undefined;
        apiKey?: string | undefined;
    } | {
        host: string;
        dialect: "qdrant";
        port?: number | undefined;
        https?: boolean | undefined;
        apiKey?: string | undefined;
        collection?: string | undefined;
    } | {
        dialect: "salesforce";
        instanceUrl: string;
        clientId: string;
        clientSecret: string;
        apiVersion?: string | undefined;
        isSandbox?: boolean | undefined;
    } | {
        dialect: "salesforce-data-cloud";
        clientId: string;
        clientSecret: string;
        loginUrl: string;
        apiVersion?: string | undefined;
        dataspace?: string | undefined;
    } | undefined;
    sharing?: {
        mode: "private" | "admins" | "all" | "users";
        userIds?: string[] | undefined;
    } | undefined;
    connectionString?: string | undefined;
}>, {
    dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "neo4j" | "falkordb" | "ultipa" | "mongodb" | "qdrant" | "redis" | "elasticsearch" | "salesforce" | "salesforce-data-cloud";
    name: string;
    params?: {
        host: string;
        database: string;
        dialect: "postgres";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        database: string;
        dialect: "mysql";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        database: string;
        dialect: "mariadb";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        database: string;
        dialect: "mssql";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        encrypt?: boolean | undefined;
        trustServerCertificate?: boolean | undefined;
    } | {
        dialect: "sqlite";
        filePath: string;
    } | {
        host: string;
        database: string;
        dialect: "cockroach";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        dialect: "oracle";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        serviceName?: string | undefined;
        sid?: string | undefined;
    } | {
        host: string;
        dialect: "clickhouse";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        https?: boolean | undefined;
    } | {
        dialect: "duckdb";
        filePath: string;
    } | {
        host: string;
        database: string;
        dialect: "mongodb";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        authSource?: string | undefined;
    } | {
        host: string;
        dialect: "neo4j";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        scheme?: "neo4j" | "neo4j+s" | "bolt" | "bolt+s" | undefined;
    } | {
        graph: string;
        host: string;
        dialect: "falkordb";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        dialect: "ultipa";
        password?: string | undefined;
        graph?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        useSSL?: boolean | undefined;
    } | {
        host: string;
        dialect: "redis";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        db?: number | undefined;
        tls?: boolean | undefined;
    } | {
        host: string;
        dialect: "elasticsearch";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        https?: boolean | undefined;
        index?: string | undefined;
        apiKey?: string | undefined;
    } | {
        host: string;
        dialect: "qdrant";
        port?: number | undefined;
        https?: boolean | undefined;
        apiKey?: string | undefined;
        collection?: string | undefined;
    } | {
        dialect: "salesforce";
        instanceUrl: string;
        clientId: string;
        clientSecret: string;
        apiVersion?: string | undefined;
        isSandbox?: boolean | undefined;
    } | {
        dialect: "salesforce-data-cloud";
        clientId: string;
        clientSecret: string;
        loginUrl: string;
        apiVersion?: string | undefined;
        dataspace?: string | undefined;
    } | undefined;
    sharing?: {
        mode: "private" | "admins" | "all" | "users";
        userIds: string[];
    } | undefined;
    connectionString?: string | undefined;
}, {
    dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "neo4j" | "falkordb" | "ultipa" | "mongodb" | "qdrant" | "redis" | "elasticsearch" | "salesforce" | "salesforce-data-cloud";
    name: string;
    params?: {
        host: string;
        database: string;
        dialect: "postgres";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        database: string;
        dialect: "mysql";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        database: string;
        dialect: "mariadb";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        database: string;
        dialect: "mssql";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        encrypt?: boolean | undefined;
        trustServerCertificate?: boolean | undefined;
    } | {
        dialect: "sqlite";
        filePath: string;
    } | {
        host: string;
        database: string;
        dialect: "cockroach";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        dialect: "oracle";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        serviceName?: string | undefined;
        sid?: string | undefined;
    } | {
        host: string;
        dialect: "clickhouse";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        https?: boolean | undefined;
    } | {
        dialect: "duckdb";
        filePath: string;
    } | {
        host: string;
        database: string;
        dialect: "mongodb";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        authSource?: string | undefined;
    } | {
        host: string;
        dialect: "neo4j";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        scheme?: "neo4j" | "neo4j+s" | "bolt" | "bolt+s" | undefined;
    } | {
        graph: string;
        host: string;
        dialect: "falkordb";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        dialect: "ultipa";
        password?: string | undefined;
        graph?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        useSSL?: boolean | undefined;
    } | {
        host: string;
        dialect: "redis";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        db?: number | undefined;
        tls?: boolean | undefined;
    } | {
        host: string;
        dialect: "elasticsearch";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        https?: boolean | undefined;
        index?: string | undefined;
        apiKey?: string | undefined;
    } | {
        host: string;
        dialect: "qdrant";
        port?: number | undefined;
        https?: boolean | undefined;
        apiKey?: string | undefined;
        collection?: string | undefined;
    } | {
        dialect: "salesforce";
        instanceUrl: string;
        clientId: string;
        clientSecret: string;
        apiVersion?: string | undefined;
        isSandbox?: boolean | undefined;
    } | {
        dialect: "salesforce-data-cloud";
        clientId: string;
        clientSecret: string;
        loginUrl: string;
        apiVersion?: string | undefined;
        dataspace?: string | undefined;
    } | undefined;
    sharing?: {
        mode: "private" | "admins" | "all" | "users";
        userIds?: string[] | undefined;
    } | undefined;
    connectionString?: string | undefined;
}>, {
    dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "neo4j" | "falkordb" | "ultipa" | "mongodb" | "qdrant" | "redis" | "elasticsearch" | "salesforce" | "salesforce-data-cloud";
    name: string;
    params?: {
        host: string;
        database: string;
        dialect: "postgres";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        database: string;
        dialect: "mysql";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        database: string;
        dialect: "mariadb";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        database: string;
        dialect: "mssql";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        encrypt?: boolean | undefined;
        trustServerCertificate?: boolean | undefined;
    } | {
        dialect: "sqlite";
        filePath: string;
    } | {
        host: string;
        database: string;
        dialect: "cockroach";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        dialect: "oracle";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        serviceName?: string | undefined;
        sid?: string | undefined;
    } | {
        host: string;
        dialect: "clickhouse";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        https?: boolean | undefined;
    } | {
        dialect: "duckdb";
        filePath: string;
    } | {
        host: string;
        database: string;
        dialect: "mongodb";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        authSource?: string | undefined;
    } | {
        host: string;
        dialect: "neo4j";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        scheme?: "neo4j" | "neo4j+s" | "bolt" | "bolt+s" | undefined;
    } | {
        graph: string;
        host: string;
        dialect: "falkordb";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        dialect: "ultipa";
        password?: string | undefined;
        graph?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        useSSL?: boolean | undefined;
    } | {
        host: string;
        dialect: "redis";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        db?: number | undefined;
        tls?: boolean | undefined;
    } | {
        host: string;
        dialect: "elasticsearch";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        https?: boolean | undefined;
        index?: string | undefined;
        apiKey?: string | undefined;
    } | {
        host: string;
        dialect: "qdrant";
        port?: number | undefined;
        https?: boolean | undefined;
        apiKey?: string | undefined;
        collection?: string | undefined;
    } | {
        dialect: "salesforce";
        instanceUrl: string;
        clientId: string;
        clientSecret: string;
        apiVersion?: string | undefined;
        isSandbox?: boolean | undefined;
    } | {
        dialect: "salesforce-data-cloud";
        clientId: string;
        clientSecret: string;
        loginUrl: string;
        apiVersion?: string | undefined;
        dataspace?: string | undefined;
    } | undefined;
    sharing?: {
        mode: "private" | "admins" | "all" | "users";
        userIds: string[];
    } | undefined;
    connectionString?: string | undefined;
}, {
    dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "neo4j" | "falkordb" | "ultipa" | "mongodb" | "qdrant" | "redis" | "elasticsearch" | "salesforce" | "salesforce-data-cloud";
    name: string;
    params?: {
        host: string;
        database: string;
        dialect: "postgres";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        database: string;
        dialect: "mysql";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        database: string;
        dialect: "mariadb";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        database: string;
        dialect: "mssql";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        encrypt?: boolean | undefined;
        trustServerCertificate?: boolean | undefined;
    } | {
        dialect: "sqlite";
        filePath: string;
    } | {
        host: string;
        database: string;
        dialect: "cockroach";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        dialect: "oracle";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        serviceName?: string | undefined;
        sid?: string | undefined;
    } | {
        host: string;
        dialect: "clickhouse";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        https?: boolean | undefined;
    } | {
        dialect: "duckdb";
        filePath: string;
    } | {
        host: string;
        database: string;
        dialect: "mongodb";
        password?: string | undefined;
        port?: number | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        authSource?: string | undefined;
    } | {
        host: string;
        dialect: "neo4j";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        scheme?: "neo4j" | "neo4j+s" | "bolt" | "bolt+s" | undefined;
    } | {
        graph: string;
        host: string;
        dialect: "falkordb";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
    } | {
        host: string;
        dialect: "ultipa";
        password?: string | undefined;
        graph?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        useSSL?: boolean | undefined;
    } | {
        host: string;
        dialect: "redis";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        db?: number | undefined;
        tls?: boolean | undefined;
    } | {
        host: string;
        dialect: "elasticsearch";
        password?: string | undefined;
        port?: number | undefined;
        database?: string | undefined;
        username?: string | undefined;
        sslMode?: "disable" | "require" | "verify-full" | undefined;
        https?: boolean | undefined;
        index?: string | undefined;
        apiKey?: string | undefined;
    } | {
        host: string;
        dialect: "qdrant";
        port?: number | undefined;
        https?: boolean | undefined;
        apiKey?: string | undefined;
        collection?: string | undefined;
    } | {
        dialect: "salesforce";
        instanceUrl: string;
        clientId: string;
        clientSecret: string;
        apiVersion?: string | undefined;
        isSandbox?: boolean | undefined;
    } | {
        dialect: "salesforce-data-cloud";
        clientId: string;
        clientSecret: string;
        loginUrl: string;
        apiVersion?: string | undefined;
        dataspace?: string | undefined;
    } | undefined;
    sharing?: {
        mode: "private" | "admins" | "all" | "users";
        userIds?: string[] | undefined;
    } | undefined;
    connectionString?: string | undefined;
}>;
export type CreateConnectionDto = z.infer<typeof CreateConnectionSchema>;
export declare const UpdateConnectionSharingSchema: z.ZodObject<{
    sharing: z.ZodEffects<z.ZodObject<{
        mode: z.ZodEnum<["private", "admins", "all", "users"]>;
        userIds: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
    }, "strip", z.ZodTypeAny, {
        mode: "private" | "admins" | "all" | "users";
        userIds: string[];
    }, {
        mode: "private" | "admins" | "all" | "users";
        userIds?: string[] | undefined;
    }>, {
        mode: "private" | "admins" | "all" | "users";
        userIds: string[];
    }, {
        mode: "private" | "admins" | "all" | "users";
        userIds?: string[] | undefined;
    }>;
}, "strip", z.ZodTypeAny, {
    sharing: {
        mode: "private" | "admins" | "all" | "users";
        userIds: string[];
    };
}, {
    sharing: {
        mode: "private" | "admins" | "all" | "users";
        userIds?: string[] | undefined;
    };
}>;
export type UpdateConnectionSharingDto = z.infer<typeof UpdateConnectionSharingSchema>;
export declare const ConnectionSummarySchema: z.ZodObject<Omit<{
    id: z.ZodString;
    name: z.ZodString;
    dialect: z.ZodEnum<["postgres", "mysql", "mariadb", "mssql", "sqlite", "cockroach", "oracle", "clickhouse", "duckdb", "mongodb", "neo4j", "falkordb", "ultipa", "qdrant", "redis", "elasticsearch", "salesforce", "salesforce-data-cloud"]>;
    connectionStringCipher: z.ZodOptional<z.ZodString>;
    /**
     * Encrypted JSON of the structured `ConnectionParams` the admin originally
     * supplied at create time. Used to re-pre-fill the edit dialog with the
     * non-secret fields (host, port, db, user...) without ever shipping the
     * decrypted secrets over HTTP. Absent for connections created from a raw
     * URL or imported via legacy paths.
     */
    paramsCipher: z.ZodOptional<z.ZodString>;
    displayHost: z.ZodOptional<z.ZodString>;
    displayDatabase: z.ZodOptional<z.ZodString>;
    readOnly: z.ZodDefault<z.ZodLiteral<true>>;
    ownerId: z.ZodString;
    sharing: z.ZodEffects<z.ZodObject<{
        mode: z.ZodEnum<["private", "admins", "all", "users"]>;
        userIds: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
    }, "strip", z.ZodTypeAny, {
        mode: "private" | "admins" | "all" | "users";
        userIds: string[];
    }, {
        mode: "private" | "admins" | "all" | "users";
        userIds?: string[] | undefined;
    }>, {
        mode: "private" | "admins" | "all" | "users";
        userIds: string[];
    }, {
        mode: "private" | "admins" | "all" | "users";
        userIds?: string[] | undefined;
    }>;
    createdAt: z.ZodString;
}, "connectionStringCipher" | "paramsCipher">, "strip", z.ZodTypeAny, {
    id: string;
    createdAt: string;
    dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "neo4j" | "falkordb" | "ultipa" | "mongodb" | "qdrant" | "redis" | "elasticsearch" | "salesforce" | "salesforce-data-cloud";
    name: string;
    readOnly: true;
    ownerId: string;
    sharing: {
        mode: "private" | "admins" | "all" | "users";
        userIds: string[];
    };
    displayHost?: string | undefined;
    displayDatabase?: string | undefined;
}, {
    id: string;
    createdAt: string;
    dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "neo4j" | "falkordb" | "ultipa" | "mongodb" | "qdrant" | "redis" | "elasticsearch" | "salesforce" | "salesforce-data-cloud";
    name: string;
    ownerId: string;
    sharing: {
        mode: "private" | "admins" | "all" | "users";
        userIds?: string[] | undefined;
    };
    displayHost?: string | undefined;
    displayDatabase?: string | undefined;
    readOnly?: true | undefined;
}>;
export type ConnectionSummary = z.infer<typeof ConnectionSummarySchema>;
export declare const DumpFormatSchema: z.ZodEnum<["sqlite-db", "sqlite-sql"]>;
export type DumpFormat = z.infer<typeof DumpFormatSchema>;
export declare const UploadDumpRequestSchema: z.ZodObject<{
    filename: z.ZodString;
    format: z.ZodEnum<["sqlite-db", "sqlite-sql"]>;
    contentBase64: z.ZodString;
}, "strip", z.ZodTypeAny, {
    filename: string;
    format: "sqlite-db" | "sqlite-sql";
    contentBase64: string;
}, {
    filename: string;
    format: "sqlite-db" | "sqlite-sql";
    contentBase64: string;
}>;
export type UploadDumpRequest = z.infer<typeof UploadDumpRequestSchema>;
export declare const UploadDumpResponseSchema: z.ZodObject<{
    filePath: z.ZodString;
    sizeBytes: z.ZodNumber;
    tables: z.ZodOptional<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    filePath: string;
    sizeBytes: number;
    tables?: number | undefined;
}, {
    filePath: string;
    sizeBytes: number;
    tables?: number | undefined;
}>;
export type UploadDumpResponse = z.infer<typeof UploadDumpResponseSchema>;
/**
 * Build a driver-ready connection string from structured params.
 * Server-side use; never expose plaintext output to clients.
 */
export declare function buildConnectionString(params: ConnectionParams): string;
/**
 * Parse a `salesforce://` connection string built by `buildConnectionString`.
 * Server-side only — input contains plaintext clientSecret.
 */
export declare function parseSalesforceConnection(cs: string): {
    instanceUrl: string;
    apiVersion: string;
    clientId: string;
    clientSecret: string;
    isSandbox: boolean;
};
/**
 * Parse a `salesforce-data-cloud://` connection string built by `buildConnectionString`.
 * Server-side only — input contains plaintext clientSecret.
 */
export declare function parseSalesforceDataCloudConnection(cs: string): {
    loginUrl: string;
    apiVersion: string;
    clientId: string;
    clientSecret: string;
    dataspace?: string;
};
//# sourceMappingURL=connection.d.ts.map