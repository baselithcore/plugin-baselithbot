import type { ConnectionParams, Dialect, SslMode } from '@dbview/shared';

export type Mode = 'fields' | 'url';

export interface FormState {
  name: string;
  dialect: Dialect;
  mode: Mode;
  url: string;
  // Network fields
  host: string;
  port: string;
  database: string;
  username: string;
  password: string;
  sslMode: SslMode;
  // Per-dialect extras
  filePath: string;
  graph: string;
  authSource: string;
  trustServerCertificate: boolean;
  // Qdrant
  apiKey: string;
  https: boolean;
  collection: string;
  // Ultipa
  useSSL: boolean;
  // Salesforce
  instanceUrl: string;
  apiVersion: string;
  clientId: string;
  clientSecret: string;
  isSandbox: boolean;
  // Salesforce Data Cloud
  sdcLoginUrl: string;
  sdcApiVersion: string;
  sdcClientId: string;
  sdcClientSecret: string;
  sdcDataspace: string;
}

export function defaultState(): FormState {
  return {
    name: '',
    dialect: 'postgres',
    mode: 'fields',
    url: '',
    host: 'localhost',
    port: '',
    database: '',
    username: '',
    password: '',
    sslMode: 'disable',
    filePath: '',
    graph: '',
    authSource: '',
    trustServerCertificate: true,
    apiKey: '',
    https: false,
    collection: '',
    useSSL: false,
    instanceUrl: '',
    apiVersion: 'v60.0',
    clientId: '',
    clientSecret: '',
    isSandbox: false,
    sdcLoginUrl: '',
    sdcApiVersion: 'v60.0',
    sdcClientId: '',
    sdcClientSecret: '',
    sdcDataspace: '',
  };
}

export const URL_PLACEHOLDER: Record<Dialect, string> = {
  postgres: 'postgres://user:pass@host:5432/db',
  mysql: 'mysql://user:pass@host:3306/db',
  mariadb: 'mysql://user:pass@host:3306/db',
  mssql: 'mssql://user:pass@host:1433/db?encrypt=true',
  sqlite: '/absolute/path/to/file.db',
  cockroach: 'postgres://user:pass@host:26257/db?sslmode=verify-full',
  oracle: 'oracle://user:pass@host:1521/ORCLPDB1',
  clickhouse: 'http://default:pass@host:8123/default',
  duckdb: '/absolute/path/to/file.duckdb',
  mongodb: 'mongodb://user:pass@host:27017/db?authSource=admin',
  neo4j: 'neo4j://user:pass@host:7687',
  falkordb: 'falkor://:pass@host:6379/graphname',
  ultipa: 'ultipa://user:pass@host:60061/myGraph',
  qdrant: 'qdrant://host:6333/collection?api-key=secret',
  redis: 'redis://:pass@host:6379/0',
  elasticsearch: 'http://elastic:pass@host:9200',
  salesforce: 'https://acme.my.salesforce.com',
  'salesforce-data-cloud': 'salesforce-data-cloud://?loginUrl=...&clientId=...&clientSecret=...',
};

/**
 * Reverse of `paramsFromState` — projects a stored `ConnectionParams` back
 * onto the flat `FormState` shape used by the create/edit form. Used by the
 * edit dialog to pre-fill non-secret fields from the server. Secret fields
 * (password, clientSecret, apiKey) are intentionally left blank when the
 * server redacts them so the UI can show the "leave blank to keep current"
 * placeholder. The caller passes `name` separately since it lives on the
 * connection, not the params.
 */
export function stateFromParams(name: string, params: ConnectionParams): FormState {
  const base = defaultState();
  base.name = name;
  base.dialect = params.dialect;
  base.mode = 'fields';
  // Always coerce numeric port to string for the input.
  const portStr = (p?: number) => (p !== undefined ? String(p) : '');
  switch (params.dialect) {
    case 'sqlite':
    case 'duckdb':
      return { ...base, filePath: params.filePath };
    case 'postgres':
    case 'mysql':
    case 'mariadb':
    case 'cockroach':
      return {
        ...base,
        host: params.host,
        port: portStr(params.port),
        database: params.database,
        username: params.username ?? '',
        password: params.password ?? '',
        sslMode: params.sslMode ?? 'disable',
      };
    case 'clickhouse':
      return {
        ...base,
        host: params.host,
        port: portStr(params.port),
        database: params.database ?? '',
        username: params.username ?? '',
        password: params.password ?? '',
        sslMode: params.sslMode ?? 'disable',
        https: !!params.https,
      };
    case 'oracle':
      return {
        ...base,
        host: params.host,
        port: portStr(params.port),
        database: params.serviceName ?? params.database ?? '',
        username: params.username ?? '',
        password: params.password ?? '',
        sslMode: params.sslMode ?? 'disable',
      };
    case 'mssql':
      return {
        ...base,
        host: params.host,
        port: portStr(params.port),
        database: params.database,
        username: params.username ?? '',
        password: params.password ?? '',
        sslMode: params.sslMode ?? 'disable',
        trustServerCertificate: params.trustServerCertificate ?? true,
      };
    case 'mongodb':
      return {
        ...base,
        host: params.host,
        port: portStr(params.port),
        database: params.database,
        username: params.username ?? '',
        password: params.password ?? '',
        sslMode: params.sslMode ?? 'disable',
        authSource: params.authSource ?? '',
      };
    case 'neo4j':
      return {
        ...base,
        host: params.host,
        port: portStr(params.port),
        database: params.database ?? '',
        username: params.username ?? '',
        password: params.password ?? '',
        sslMode: params.sslMode ?? 'disable',
      };
    case 'falkordb':
      return {
        ...base,
        host: params.host,
        port: portStr(params.port),
        graph: params.graph,
        username: params.username ?? '',
        password: params.password ?? '',
      };
    case 'ultipa':
      return {
        ...base,
        host: params.host,
        port: portStr(params.port),
        graph: params.graph ?? '',
        username: params.username ?? '',
        password: params.password ?? '',
        useSSL: !!params.useSSL,
      };
    case 'qdrant':
      return {
        ...base,
        host: params.host,
        port: portStr(params.port),
        https: !!params.https,
        apiKey: params.apiKey ?? '',
        collection: params.collection ?? '',
      };
    case 'redis':
      return {
        ...base,
        host: params.host,
        port: portStr(params.port),
        database: params.db !== undefined ? String(params.db) : '',
        username: params.username ?? '',
        password: params.password ?? '',
        useSSL: !!params.tls,
      };
    case 'elasticsearch':
      return {
        ...base,
        host: params.host,
        port: portStr(params.port),
        username: params.username ?? '',
        password: params.password ?? '',
        https: !!params.https,
        apiKey: params.apiKey ?? '',
      };
    case 'salesforce':
      return {
        ...base,
        instanceUrl: params.instanceUrl,
        apiVersion: params.apiVersion ?? 'v60.0',
        clientId: params.clientId,
        clientSecret: params.clientSecret ?? '',
        isSandbox: !!params.isSandbox,
      };
    case 'salesforce-data-cloud':
      return {
        ...base,
        sdcLoginUrl: params.loginUrl,
        sdcApiVersion: params.apiVersion ?? 'v60.0',
        sdcClientId: params.clientId,
        sdcClientSecret: params.clientSecret ?? '',
        sdcDataspace: params.dataspace ?? '',
      };
  }
}

export function paramsFromState(s: FormState): ConnectionParams | null {
  const port = s.port ? Number.parseInt(s.port, 10) : undefined;
  const sslMode = s.sslMode === 'disable' ? undefined : s.sslMode;
  const username = s.username.trim() || undefined;
  const password = s.password === '' ? undefined : s.password;

  switch (s.dialect) {
    case 'sqlite':
      if (!s.filePath.trim()) return null;
      return { dialect: 'sqlite', filePath: s.filePath.trim() };
    case 'duckdb':
      if (!s.filePath.trim()) return null;
      return { dialect: 'duckdb', filePath: s.filePath.trim() };
    case 'postgres':
    case 'mysql':
    case 'mariadb':
    case 'cockroach':
      if (!s.host.trim() || !s.database.trim()) return null;
      return {
        dialect: s.dialect,
        host: s.host.trim(),
        port,
        database: s.database.trim(),
        username,
        password,
        sslMode,
      };
    case 'clickhouse':
      if (!s.host.trim()) return null;
      return {
        dialect: 'clickhouse',
        host: s.host.trim(),
        port,
        database: s.database.trim() || undefined,
        username,
        password,
        sslMode,
        https: s.https,
      };
    case 'oracle':
      if (!s.host.trim() || !s.database.trim()) return null;
      return {
        dialect: 'oracle',
        host: s.host.trim(),
        port,
        database: s.database.trim(),
        serviceName: s.database.trim(),
        username,
        password,
        sslMode,
      };
    case 'mssql':
      if (!s.host.trim() || !s.database.trim()) return null;
      return {
        dialect: 'mssql',
        host: s.host.trim(),
        port,
        database: s.database.trim(),
        username,
        password,
        sslMode,
        trustServerCertificate: s.trustServerCertificate,
      };
    case 'mongodb':
      if (!s.host.trim() || !s.database.trim()) return null;
      return {
        dialect: 'mongodb',
        host: s.host.trim(),
        port,
        database: s.database.trim(),
        username,
        password,
        sslMode,
        authSource: s.authSource.trim() || undefined,
      };
    case 'neo4j':
      if (!s.host.trim()) return null;
      return {
        dialect: 'neo4j',
        host: s.host.trim(),
        port,
        database: s.database.trim() || undefined,
        username,
        password,
        sslMode,
      };
    case 'falkordb':
      if (!s.host.trim() || !s.graph.trim()) return null;
      return {
        dialect: 'falkordb',
        host: s.host.trim(),
        port,
        graph: s.graph.trim(),
        username,
        password,
      };
    case 'ultipa':
      if (!s.host.trim()) return null;
      return {
        dialect: 'ultipa',
        host: s.host.trim(),
        port,
        graph: s.graph.trim() || undefined,
        username,
        password,
        useSSL: s.useSSL,
      };
    case 'qdrant':
      if (!s.host.trim()) return null;
      return {
        dialect: 'qdrant',
        host: s.host.trim(),
        port,
        https: s.https,
        apiKey: s.apiKey.trim() || undefined,
        collection: s.collection.trim() || undefined,
      };
    case 'redis': {
      if (!s.host.trim()) return null;
      const dbIdx = s.database.trim() ? Number.parseInt(s.database.trim(), 10) : undefined;
      return {
        dialect: 'redis',
        host: s.host.trim(),
        port,
        db: Number.isFinite(dbIdx) ? dbIdx : undefined,
        username,
        password,
        tls: s.useSSL,
      };
    }
    case 'elasticsearch': {
      if (!s.host.trim()) return null;
      return {
        dialect: 'elasticsearch',
        host: s.host.trim(),
        port,
        username,
        password,
        https: s.https,
        apiKey: s.apiKey.trim() || undefined,
      };
    }
    case 'salesforce': {
      const instanceUrl = s.instanceUrl.trim().replace(/\/+$/, '');
      const clientId = s.clientId.trim();
      if (!instanceUrl || !clientId || !s.clientSecret) return null;
      const apiVersion = s.apiVersion.trim() || 'v60.0';
      return {
        dialect: 'salesforce',
        instanceUrl,
        apiVersion,
        clientId,
        clientSecret: s.clientSecret,
        isSandbox: s.isSandbox,
      };
    }
    case 'salesforce-data-cloud': {
      const loginUrl = s.sdcLoginUrl.trim().replace(/\/+$/, '');
      const clientId = s.sdcClientId.trim();
      if (!loginUrl || !clientId || !s.sdcClientSecret) return null;
      const apiVersion = s.sdcApiVersion.trim() || 'v60.0';
      const dataspace = s.sdcDataspace.trim() || undefined;
      return {
        dialect: 'salesforce-data-cloud',
        loginUrl,
        apiVersion,
        clientId,
        clientSecret: s.sdcClientSecret,
        dataspace,
      };
    }
  }
}
