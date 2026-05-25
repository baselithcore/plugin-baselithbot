import { z } from 'zod';
import { DialectSchema, DIALECT_META, type Dialect } from './dialect.js';

export const SslModeSchema = z.enum(['disable', 'require', 'verify-full']);
export type SslMode = z.infer<typeof SslModeSchema>;

const NetworkBaseSchema = z.object({
  host: z.string().min(1).max(253),
  port: z.number().int().min(1).max(65535).optional(),
  database: z.string().min(1).max(128),
  username: z.string().max(128).optional(),
  password: z.string().max(512).optional(),
  sslMode: SslModeSchema.optional(),
});

export const PostgresParamsSchema = NetworkBaseSchema.extend({
  dialect: z.literal('postgres'),
});
export const MysqlParamsSchema = NetworkBaseSchema.extend({
  dialect: z.literal('mysql'),
});
export const MariadbParamsSchema = NetworkBaseSchema.extend({
  dialect: z.literal('mariadb'),
});
export const MssqlParamsSchema = NetworkBaseSchema.extend({
  dialect: z.literal('mssql'),
  encrypt: z.boolean().optional(),
  trustServerCertificate: z.boolean().optional(),
});
export const SqliteParamsSchema = z.object({
  dialect: z.literal('sqlite'),
  filePath: z.string().min(1).max(2048),
});
export const CockroachParamsSchema = NetworkBaseSchema.extend({
  dialect: z.literal('cockroach'),
});
export const OracleParamsSchema = NetworkBaseSchema.partial({ database: true }).extend({
  dialect: z.literal('oracle'),
  /** Oracle service name (preferred) or SID. Stored in `database` field for unified URL parsing. */
  serviceName: z.string().min(1).max(128).optional(),
  sid: z.string().min(1).max(128).optional(),
});
export const ClickhouseParamsSchema = NetworkBaseSchema.partial({
  database: true,
  username: true,
}).extend({
  dialect: z.literal('clickhouse'),
  /** Use HTTPS interface (port 8443 typically). */
  https: z.boolean().optional(),
});
export const DuckdbParamsSchema = z.object({
  dialect: z.literal('duckdb'),
  /** Filesystem path to .duckdb file, or `:memory:` for ephemeral. */
  filePath: z.string().min(1).max(2048),
});
export const MongoParamsSchema = NetworkBaseSchema.extend({
  dialect: z.literal('mongodb'),
  authSource: z.string().max(128).optional(),
});
export const Neo4jParamsSchema = NetworkBaseSchema.partial({ database: true }).extend({
  dialect: z.literal('neo4j'),
  database: z.string().max(128).optional(),
  scheme: z.enum(['neo4j', 'neo4j+s', 'bolt', 'bolt+s']).optional(),
});
export const FalkorParamsSchema = NetworkBaseSchema.partial({
  username: true,
  database: true,
  sslMode: true,
}).extend({
  dialect: z.literal('falkordb'),
  graph: z.string().min(1).max(128),
});

export const UltipaParamsSchema = NetworkBaseSchema.partial({
  database: true,
  sslMode: true,
}).extend({
  dialect: z.literal('ultipa'),
  /** Default graph for the session (server-side `USE GRAPH`). */
  graph: z.string().min(1).max(128).optional(),
  /** Enable TLS for the gRPC channel. */
  useSSL: z.boolean().optional(),
});

export const RedisParamsSchema = NetworkBaseSchema.partial({
  database: true,
  username: true,
  sslMode: true,
}).extend({
  dialect: z.literal('redis'),
  /** Logical DB index (0-15 typical). */
  db: z.number().int().min(0).max(15).optional(),
  /** Enable TLS. */
  tls: z.boolean().optional(),
});

export const ElasticsearchParamsSchema = NetworkBaseSchema.partial({
  database: true,
  username: true,
  sslMode: true,
}).extend({
  dialect: z.literal('elasticsearch'),
  /** Use HTTPS instead of HTTP. */
  https: z.boolean().optional(),
  /** Optional default index pattern to focus the UI. */
  index: z.string().max(256).optional(),
  /** API key for ES Cloud or 8.x token-based auth. */
  apiKey: z.string().max(512).optional(),
});

export const QdrantParamsSchema = z.object({
  dialect: z.literal('qdrant'),
  host: z.string().min(1).max(253),
  port: z.number().int().min(1).max(65535).optional(),
  /** TLS via https. Default false (plain HTTP for local). */
  https: z.boolean().optional(),
  /** API key sent as `api-key` header. Optional for local dev. */
  apiKey: z.string().max(512).optional(),
  /** Optional default collection to focus the UI on. */
  collection: z.string().max(128).optional(),
});

/**
 * Salesforce connection params. Authentication: OAuth 2.0 Client Credentials Flow only
 * (Connected App with "Enable Client Credentials Flow" + a "Run As" user).
 * Username-Password is deprecated by Salesforce; JWT Bearer is not yet implemented here.
 */
export const SalesforceParamsSchema = z.object({
  dialect: z.literal('salesforce'),
  /** Full instance URL, e.g. `https://acme.my.salesforce.com` (no trailing slash). */
  instanceUrl: z
    .string()
    .min(8)
    .max(512)
    .regex(/^https?:\/\//, 'instanceUrl must start with http:// or https://'),
  /** Salesforce REST API version, e.g. `v60.0`. Default `v60.0`. */
  apiVersion: z
    .string()
    .max(8)
    .regex(/^v\d{2}\.\d$/, 'apiVersion must match `vNN.N` (e.g. v60.0)')
    .optional(),
  /** Connected App consumer key. */
  clientId: z.string().min(1).max(512),
  /** Connected App consumer secret (encrypted at rest). */
  clientSecret: z.string().min(1).max(512),
  /** Sandbox flag — informational; Client Credentials uses instanceUrl directly. */
  isSandbox: z.boolean().optional(),
});

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
export const SalesforceDataCloudParamsSchema = z.object({
  dialect: z.literal('salesforce-data-cloud'),
  /** Core login / My Domain URL, e.g. `https://acme.my.salesforce.com`. */
  loginUrl: z
    .string()
    .min(8)
    .max(512)
    .regex(/^https?:\/\//, 'loginUrl must start with http:// or https://'),
  /** Salesforce Data Cloud REST API version path segment, default `v60.0`. */
  apiVersion: z
    .string()
    .max(8)
    .regex(/^v\d{2,3}\.\d$/, 'apiVersion must match `vNN.N` (e.g. v60.0)')
    .optional(),
  /** Connected App consumer key (client_id). */
  clientId: z.string().min(1).max(512),
  /** Connected App consumer secret (client_secret). Encrypted at rest. */
  clientSecret: z.string().min(1).max(512),
  /**
   * Optional dataspace. Data Cloud orgs default to `default`; when an org
   * defines multiple dataspaces (brand-level data isolation) callers may pick
   * one. Currently informational — query endpoint resolves it via auth scope.
   */
  dataspace: z.string().min(1).max(128).optional(),
});

export const ConnectionParamsSchema = z.discriminatedUnion('dialect', [
  PostgresParamsSchema,
  MysqlParamsSchema,
  MariadbParamsSchema,
  MssqlParamsSchema,
  SqliteParamsSchema,
  CockroachParamsSchema,
  OracleParamsSchema,
  ClickhouseParamsSchema,
  DuckdbParamsSchema,
  MongoParamsSchema,
  Neo4jParamsSchema,
  FalkorParamsSchema,
  UltipaParamsSchema,
  QdrantParamsSchema,
  RedisParamsSchema,
  ElasticsearchParamsSchema,
  SalesforceParamsSchema,
  SalesforceDataCloudParamsSchema,
]);
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
export const ConnectionSharingSchema = z
  .object({
    mode: z.enum(['private', 'admins', 'all', 'users']),
    userIds: z.array(z.string().uuid()).default([]),
  })
  .refine((s) => s.mode !== 'users' || s.userIds.length > 0, {
    message: 'sharing.userIds must not be empty when mode = "users"',
    path: ['userIds'],
  });
export type ConnectionSharing = z.infer<typeof ConnectionSharingSchema>;

export const ConnectionConfigSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).max(64),
  dialect: DialectSchema,
  connectionStringCipher: z.string().optional(),
  /**
   * Encrypted JSON of the structured `ConnectionParams` the admin originally
   * supplied at create time. Used to re-pre-fill the edit dialog with the
   * non-secret fields (host, port, db, user...) without ever shipping the
   * decrypted secrets over HTTP. Absent for connections created from a raw
   * URL or imported via legacy paths.
   */
  paramsCipher: z.string().optional(),
  displayHost: z.string().optional(),
  displayDatabase: z.string().optional(),
  readOnly: z.literal(true).default(true),
  ownerId: z.string().uuid(),
  sharing: ConnectionSharingSchema,
  createdAt: z.string().datetime(),
});
export type ConnectionConfig = z.infer<typeof ConnectionConfigSchema>;

export const CreateConnectionSchema = z
  .object({
    name: z.string().min(1).max(64),
    dialect: DialectSchema,
    params: ConnectionParamsSchema.optional(),
    connectionString: z.string().min(1).optional(),
    sharing: ConnectionSharingSchema.optional(),
  })
  .refine((v) => !!v.params || !!v.connectionString, {
    message: 'Either params or connectionString is required',
    path: ['params'],
  })
  .refine((v) => !v.params || v.params.dialect === v.dialect, {
    message: 'params.dialect must match top-level dialect',
    path: ['params', 'dialect'],
  });
export type CreateConnectionDto = z.infer<typeof CreateConnectionSchema>;

export const UpdateConnectionSharingSchema = z.object({
  sharing: ConnectionSharingSchema,
});
export type UpdateConnectionSharingDto = z.infer<typeof UpdateConnectionSharingSchema>;

export const ConnectionSummarySchema = ConnectionConfigSchema.omit({
  connectionStringCipher: true,
  paramsCipher: true,
});
export type ConnectionSummary = z.infer<typeof ConnectionSummarySchema>;

export const DumpFormatSchema = z.enum(['sqlite-db', 'sqlite-sql']);
export type DumpFormat = z.infer<typeof DumpFormatSchema>;

export const UploadDumpRequestSchema = z.object({
  filename: z
    .string()
    .min(1)
    .max(255)
    .regex(/^[A-Za-z0-9._-]+$/, 'filename may contain only letters, digits, dot, dash, underscore'),
  format: DumpFormatSchema,
  contentBase64: z.string().min(1).max(400_000_000),
});
export type UploadDumpRequest = z.infer<typeof UploadDumpRequestSchema>;

export const UploadDumpResponseSchema = z.object({
  filePath: z.string(),
  sizeBytes: z.number().int().nonnegative(),
  tables: z.number().int().nonnegative().optional(),
});
export type UploadDumpResponse = z.infer<typeof UploadDumpResponseSchema>;

/**
 * Build a driver-ready connection string from structured params.
 * Server-side use; never expose plaintext output to clients.
 */
export function buildConnectionString(params: ConnectionParams): string {
  switch (params.dialect) {
    case 'sqlite':
      return params.filePath;
    case 'postgres':
      return buildUrl('postgres:', params, defaultPort('postgres'), pgSslQuery(params.sslMode));
    case 'cockroach':
      return buildUrl('postgres:', params, defaultPort('cockroach'), pgSslQuery(params.sslMode));
    case 'oracle': {
      const port = params.port ?? defaultPort('oracle');
      const auth =
        params.username !== undefined
          ? `${encodeURIComponent(params.username)}:${encodeURIComponent(params.password ?? '')}@`
          : '';
      const service = params.serviceName ?? params.database ?? params.sid;
      if (!service) {
        throw new Error('oracle: serviceName, database, or sid is required');
      }
      const path = `/${encodeURIComponent(service)}`;
      const qs = new URLSearchParams();
      if (params.sid && !params.serviceName) qs.set('sid', params.sid);
      const tail = qs.toString() ? `?${qs.toString()}` : '';
      return `oracle://${auth}${params.host}:${port}${path}${tail}`;
    }
    case 'clickhouse': {
      const port = params.port ?? defaultPort('clickhouse');
      const scheme = params.https ? 'https' : 'http';
      const auth =
        params.username !== undefined
          ? `${encodeURIComponent(params.username)}:${encodeURIComponent(params.password ?? '')}@`
          : '';
      const path = params.database ? `/${encodeURIComponent(params.database)}` : '';
      return `${scheme}://${auth}${params.host}:${port}${path}`;
    }
    case 'duckdb':
      return params.filePath;
    case 'mysql':
      return buildUrl('mysql:', params, defaultPort('mysql'), mysqlSslQuery(params.sslMode));
    case 'mariadb':
      return buildUrl('mysql:', params, defaultPort('mariadb'), mysqlSslQuery(params.sslMode));
    case 'mssql': {
      const port = params.port ?? defaultPort('mssql');
      const encrypt = params.encrypt ?? params.sslMode !== 'disable';
      const trust = params.trustServerCertificate ?? params.sslMode !== 'verify-full';
      const auth =
        params.username !== undefined
          ? `${encodeURIComponent(params.username)}:${encodeURIComponent(params.password ?? '')}@`
          : '';
      const qs = new URLSearchParams();
      qs.set('encrypt', encrypt ? 'true' : 'false');
      qs.set('trustServerCertificate', trust ? 'true' : 'false');
      return `mssql://${auth}${params.host}:${port}/${encodeURIComponent(params.database)}?${qs.toString()}`;
    }
    case 'mongodb': {
      const port = params.port ?? defaultPort('mongodb');
      const auth =
        params.username !== undefined
          ? `${encodeURIComponent(params.username)}:${encodeURIComponent(params.password ?? '')}@`
          : '';
      const qs = new URLSearchParams();
      if (params.authSource) qs.set('authSource', params.authSource);
      if (params.sslMode === 'require' || params.sslMode === 'verify-full') {
        qs.set('tls', 'true');
        if (params.sslMode === 'require') qs.set('tlsAllowInvalidCertificates', 'true');
      }
      const tail = qs.toString() ? `?${qs.toString()}` : '';
      return `mongodb://${auth}${params.host}:${port}/${encodeURIComponent(params.database)}${tail}`;
    }
    case 'neo4j': {
      const scheme = params.scheme ?? (params.sslMode === 'verify-full' ? 'neo4j+s' : 'neo4j');
      const port = params.port ?? defaultPort('neo4j');
      const auth =
        params.username !== undefined
          ? `${encodeURIComponent(params.username)}:${encodeURIComponent(params.password ?? '')}@`
          : '';
      const path = params.database ? `/${encodeURIComponent(params.database)}` : '';
      return `${scheme}://${auth}${params.host}:${port}${path}`;
    }
    case 'falkordb': {
      const port = params.port ?? defaultPort('falkordb');
      const auth =
        params.username !== undefined || params.password !== undefined
          ? `${encodeURIComponent(params.username ?? '')}:${encodeURIComponent(params.password ?? '')}@`
          : '';
      return `falkor://${auth}${params.host}:${port}/${encodeURIComponent(params.graph)}`;
    }
    case 'ultipa': {
      const port = params.port ?? defaultPort('ultipa');
      const scheme = params.useSSL ? 'ultipas' : 'ultipa';
      const auth =
        params.username !== undefined
          ? `${encodeURIComponent(params.username)}:${encodeURIComponent(params.password ?? '')}@`
          : '';
      const path = params.graph ? `/${encodeURIComponent(params.graph)}` : '';
      return `${scheme}://${auth}${params.host}:${port}${path}`;
    }
    case 'qdrant': {
      const port = params.port ?? defaultPort('qdrant');
      const scheme = params.https ? 'qdrants' : 'qdrant';
      const apiKey = params.apiKey ? `?api-key=${encodeURIComponent(params.apiKey)}` : '';
      const path = params.collection ? `/${encodeURIComponent(params.collection)}` : '';
      return `${scheme}://${params.host}:${port}${path}${apiKey}`;
    }
    case 'redis': {
      const port = params.port ?? defaultPort('redis');
      const scheme = params.tls ? 'rediss' : 'redis';
      const auth =
        params.username !== undefined || params.password !== undefined
          ? `${encodeURIComponent(params.username ?? '')}:${encodeURIComponent(params.password ?? '')}@`
          : '';
      const path = params.db !== undefined ? `/${params.db}` : '';
      return `${scheme}://${auth}${params.host}:${port}${path}`;
    }
    case 'elasticsearch': {
      const port = params.port ?? defaultPort('elasticsearch');
      const scheme = params.https ? 'https' : 'http';
      const auth =
        params.username !== undefined
          ? `${encodeURIComponent(params.username)}:${encodeURIComponent(params.password ?? '')}@`
          : '';
      const qs = new URLSearchParams();
      if (params.apiKey) qs.set('api-key', params.apiKey);
      if (params.index) qs.set('index', params.index);
      const tail = qs.toString() ? `?${qs.toString()}` : '';
      return `${scheme}://${auth}${params.host}:${port}${tail}`;
    }
    case 'salesforce': {
      // Encode params into a custom `salesforce://` URL. clientSecret is encoded in userInfo
      // and the entire string is encrypted at rest before persistence.
      const apiVersion = params.apiVersion ?? 'v60.0';
      const instance = params.instanceUrl.replace(/\/+$/, '');
      const qs = new URLSearchParams();
      qs.set('instanceUrl', instance);
      qs.set('apiVersion', apiVersion);
      qs.set('clientId', params.clientId);
      qs.set('clientSecret', params.clientSecret);
      if (params.isSandbox) qs.set('sandbox', 'true');
      return `salesforce://?${qs.toString()}`;
    }
    case 'salesforce-data-cloud': {
      const apiVersion = params.apiVersion ?? 'v60.0';
      const login = params.loginUrl.replace(/\/+$/, '');
      const qs = new URLSearchParams();
      qs.set('loginUrl', login);
      qs.set('apiVersion', apiVersion);
      qs.set('clientId', params.clientId);
      qs.set('clientSecret', params.clientSecret);
      if (params.dataspace) qs.set('dataspace', params.dataspace);
      return `salesforce-data-cloud://?${qs.toString()}`;
    }
  }
}

/**
 * Parse a `salesforce://` connection string built by `buildConnectionString`.
 * Server-side only — input contains plaintext clientSecret.
 */
export function parseSalesforceConnection(cs: string): {
  instanceUrl: string;
  apiVersion: string;
  clientId: string;
  clientSecret: string;
  isSandbox: boolean;
} {
  if (!cs.startsWith('salesforce://')) {
    throw new Error('salesforce: connection string must start with salesforce://');
  }
  const qIdx = cs.indexOf('?');
  if (qIdx === -1) throw new Error('salesforce: connection string missing query params');
  const qs = new URLSearchParams(cs.slice(qIdx + 1));
  const instanceUrl = qs.get('instanceUrl');
  const apiVersion = qs.get('apiVersion') ?? 'v60.0';
  const clientId = qs.get('clientId');
  const clientSecret = qs.get('clientSecret');
  if (!instanceUrl || !clientId || !clientSecret) {
    throw new Error('salesforce: instanceUrl, clientId, clientSecret are required');
  }
  return {
    instanceUrl,
    apiVersion,
    clientId,
    clientSecret,
    isSandbox: qs.get('sandbox') === 'true',
  };
}

/**
 * Parse a `salesforce-data-cloud://` connection string built by `buildConnectionString`.
 * Server-side only — input contains plaintext clientSecret.
 */
export function parseSalesforceDataCloudConnection(cs: string): {
  loginUrl: string;
  apiVersion: string;
  clientId: string;
  clientSecret: string;
  dataspace?: string;
} {
  if (!cs.startsWith('salesforce-data-cloud://')) {
    throw new Error(
      'salesforce-data-cloud: connection string must start with salesforce-data-cloud://'
    );
  }
  const qIdx = cs.indexOf('?');
  if (qIdx === -1) {
    throw new Error('salesforce-data-cloud: connection string missing query params');
  }
  const qs = new URLSearchParams(cs.slice(qIdx + 1));
  const loginUrl = qs.get('loginUrl');
  const apiVersion = qs.get('apiVersion') ?? 'v60.0';
  const clientId = qs.get('clientId');
  const clientSecret = qs.get('clientSecret');
  if (!loginUrl || !clientId || !clientSecret) {
    throw new Error('salesforce-data-cloud: loginUrl, clientId, clientSecret are required');
  }
  const dataspace = qs.get('dataspace') ?? undefined;
  return { loginUrl, apiVersion, clientId, clientSecret, dataspace: dataspace || undefined };
}

function defaultPort(d: Dialect): number {
  return DIALECT_META[d].defaultPort ?? 0;
}

function buildUrl(
  scheme: string,
  p: { host: string; port?: number; database: string; username?: string; password?: string },
  fallbackPort: number,
  query: string
): string {
  const port = p.port ?? fallbackPort;
  const auth =
    p.username !== undefined
      ? `${encodeURIComponent(p.username)}:${encodeURIComponent(p.password ?? '')}@`
      : '';
  const tail = query ? `?${query}` : '';
  return `${scheme}//${auth}${p.host}:${port}/${encodeURIComponent(p.database)}${tail}`;
}

function pgSslQuery(mode?: SslMode): string {
  if (!mode || mode === 'disable') return '';
  if (mode === 'require') return 'sslmode=require';
  return 'sslmode=verify-full';
}

function mysqlSslQuery(mode?: SslMode): string {
  if (!mode || mode === 'disable') return '';
  if (mode === 'require') return 'ssl=true';
  return 'ssl=true&ssl-mode=VERIFY_IDENTITY';
}
