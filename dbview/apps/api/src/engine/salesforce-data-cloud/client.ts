import { parseSalesforceDataCloudConnection } from '@dbview/shared';

export interface SalesforceDataCloudCredentials {
  loginUrl: string;
  apiVersion: string;
  clientId: string;
  clientSecret: string;
  dataspace?: string;
}

interface CdpSession {
  /** Data-Cloud-scoped access token used as Bearer on /api/v2/query. */
  cdpToken: string;
  /** Data Cloud tenant base URL returned by the token-exchange endpoint. */
  tenantUrl: string;
  /** Epoch ms at which the cached session should be refreshed (issuer expiry minus a safety buffer). */
  refreshAt: number;
}

/**
 * Thin Salesforce Data Cloud REST client.
 *
 * Auth chain (Client Credentials Flow, MVP):
 *   1. POST {loginUrl}/services/oauth2/token (grant_type=client_credentials)
 *      → Core access_token + instance_url.
 *   2. POST {instance_url}/services/a360/token (grant_type=urn:salesforce:grant-type:external:cdp,
 *      subject_token=<core access_token>, subject_token_type=access_token)
 *      → Data Cloud access_token + instance_url (the CDP tenant host).
 *
 * The CDP token + tenant URL are cached in memory and reused until shortly
 * before issuer expiry. On a 401 from the query endpoint the cache is
 * invalidated and the request is retried exactly once.
 *
 * Endpoints used at query time:
 *   - POST {tenantUrl}/api/v2/query              — submit ANSI SQL.
 *   - GET  {tenantUrl}/api/v2/query/{nextBatchId} — fetch subsequent pages.
 *   - GET  {tenantUrl}/api/v2/metadata           — list DMOs (introspection).
 *   - GET  {tenantUrl}/api/v2/metadata/{entityName} — describe a single DMO.
 */
export class SalesforceDataCloudClient {
  private readonly creds: SalesforceDataCloudCredentials;
  private session: CdpSession | null = null;
  /** Configurable fetch implementation — overridable for tests. */
  private readonly httpFetch: typeof fetch;

  constructor(connectionString: string, opts?: { fetch?: typeof fetch }) {
    this.creds = parseSalesforceDataCloudConnection(connectionString);
    this.httpFetch = opts?.fetch ?? fetch;
  }

  /** Lightweight reachability probe — exchanges credentials without listing DMOs. */
  async ping(): Promise<void> {
    await this.getSession();
  }

  /**
   * Submit a single SDC SQL statement. The Data Cloud Query v2 endpoint is
   * read-only by design; safety enforcement happens upstream via the SQL
   * validator before this is called.
   *
   * Pagination: if `done=false`, the server returns `nextBatchId`. Callers
   * (Executor) loop through `nextPage()` until `done` or rowLimit reached.
   */
  async query(sql: string): Promise<SdcQueryPage> {
    return this.request<SdcQueryPage>('POST', '/api/v2/query', { sql });
  }

  /** Fetch the next page in a paginated query. */
  async nextPage(nextBatchId: string): Promise<SdcQueryPage> {
    if (!/^[A-Za-z0-9_-]+$/.test(nextBatchId)) {
      throw new Error('Invalid nextBatchId.');
    }
    return this.request<SdcQueryPage>('GET', `/api/v2/query/${nextBatchId}`);
  }

  /**
   * List all metadata entities (DMOs / DLOs / CIOs) on the tenant.
   *
   * Salesforce Data Cloud Connect API splits versions per surface:
   *   - Metadata APIs live under `/api/v1/metadata`.
   *   - Query API lives under `/api/v2/query`.
   * Using `/api/v2/metadata` returns HTTP 404 even on a valid CDP tenant.
   */
  async listEntities(): Promise<SdcMetadataListResponse> {
    return this.request<SdcMetadataListResponse>('GET', '/api/v1/metadata');
  }

  /**
   * Describe a single entity by API name (returns full field list).
   *
   * Salesforce Data Cloud does not expose `/api/v1/metadata/{name}` as a path
   * — that returns HTTP 404 "No static resource". The supported shape is the
   * same list endpoint with an `entityName` query parameter, which returns a
   * `{ metadata: [entity] }` envelope containing a single fully-described entity.
   */
  async describeEntity(entityName: string): Promise<SdcMetadataEntity> {
    if (!/^[A-Za-z0-9_]+$/.test(entityName)) {
      throw new Error(`Invalid entity name: ${entityName}`);
    }
    const wrapped = await this.request<SdcMetadataListResponse>(
      'GET',
      `/api/v1/metadata?entityName=${encodeURIComponent(entityName)}`
    );
    const first = wrapped.metadata?.[0];
    if (!first) {
      throw new Error(`Data Cloud metadata for '${entityName}' returned no entities.`);
    }
    return first;
  }

  async close(): Promise<void> {
    this.session = null;
  }

  /** Returns the parsed credentials (read-only) — useful for introspector context. */
  get credentials(): Readonly<SalesforceDataCloudCredentials> {
    return this.creds;
  }

  private async getSession(): Promise<CdpSession> {
    if (this.session && Date.now() < this.session.refreshAt) return this.session;

    const core = await this.fetchCoreToken();
    const cdp = await this.exchangeForDataCloudToken(core);
    this.session = cdp;
    return cdp;
  }

  private invalidate(): void {
    this.session = null;
  }

  private async fetchCoreToken(): Promise<{ token: string; instanceUrl: string }> {
    const tokenUrl = `${this.creds.loginUrl.replace(/\/+$/, '')}/services/oauth2/token`;
    const body = new URLSearchParams({
      grant_type: 'client_credentials',
      client_id: this.creds.clientId,
      client_secret: this.creds.clientSecret,
    });
    const res = await this.httpFetch(tokenUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    });
    if (!res.ok) {
      const text = await safeReadText(res);
      throw new Error(
        `Salesforce core auth failed (${res.status}): ${truncate(text, 240) || res.statusText}`
      );
    }
    const data = (await res.json()) as {
      access_token?: string;
      instance_url?: string;
    };
    if (!data.access_token || !data.instance_url) {
      throw new Error('Salesforce core auth response missing access_token or instance_url');
    }
    return {
      token: data.access_token,
      instanceUrl: data.instance_url.replace(/\/+$/, ''),
    };
  }

  private async exchangeForDataCloudToken(core: {
    token: string;
    instanceUrl: string;
  }): Promise<CdpSession> {
    const exchangeUrl = `${core.instanceUrl}/services/a360/token`;
    const body = new URLSearchParams({
      grant_type: 'urn:salesforce:grant-type:external:cdp',
      subject_token: core.token,
      subject_token_type: 'urn:ietf:params:oauth:token-type:access_token',
    });
    if (this.creds.dataspace) {
      // Data Cloud accepts an optional `dataspace` form parameter on token exchange.
      body.set('dataspace', this.creds.dataspace);
    }
    const res = await this.httpFetch(exchangeUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    });
    if (!res.ok) {
      const text = await safeReadText(res);
      throw new Error(
        `Salesforce Data Cloud token exchange failed (${res.status}): ${truncate(text, 240) || res.statusText}`
      );
    }
    const data = (await res.json()) as {
      access_token?: string;
      instance_url?: string;
      expires_in?: number;
    };
    if (!data.access_token || !data.instance_url) {
      throw new Error('Data Cloud token exchange response missing access_token or instance_url');
    }
    const ttlSec =
      typeof data.expires_in === 'number' && data.expires_in > 60 ? data.expires_in : 1800;
    const tenantUrl = normalizeTenantUrl(data.instance_url);
    return {
      cdpToken: data.access_token,
      tenantUrl,
      refreshAt: Date.now() + (ttlSec - 60) * 1000,
    };
  }

  private async request<T>(
    method: 'GET' | 'POST',
    path: string,
    body?: unknown,
    _retried = false
  ): Promise<T> {
    const session = await this.getSession();
    const url = path.startsWith('http') ? path : `${session.tenantUrl}${path}`;
    const headers: Record<string, string> = {
      Authorization: `Bearer ${session.cdpToken}`,
      Accept: 'application/json',
    };
    let payload: BodyInit | undefined;
    if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
      payload = JSON.stringify(body);
    }
    const res = await this.httpFetch(url, { method, headers, body: payload });
    if (res.status === 401 && !_retried) {
      this.invalidate();
      return this.request<T>(method, path, body, true);
    }
    if (!res.ok) {
      const text = await safeReadText(res);
      throw new Error(
        `Salesforce Data Cloud ${method} ${path} failed (${res.status}): ${truncate(text, 320) || res.statusText}`
      );
    }
    return (await res.json()) as T;
  }
}

/**
 * Wire-level shape of a `/api/v2/query` response page.
 *
 * Salesforce Data Cloud returns rows positionally as arrays — NOT as objects
 * keyed by column name. The column ↔ index mapping is recovered from
 * `metadata[col].placeInOrder`. Earlier (`/api/v1/query`) endpoints used
 * row objects; v2 standardised on the positional shape for streaming.
 *
 * Older SDC tenants occasionally still emit row objects; the executor handles
 * both shapes to stay forward/backward compatible.
 */
export interface SdcQueryPage {
  /** Either positional rows (`unknown[][]`) or legacy keyed rows (`Record<string,unknown>[]`). */
  data: unknown[][] | Array<Record<string, unknown>>;
  /** Column metadata. `placeInOrder` indexes into the positional row arrays. */
  metadata?: Record<string, { type: string; placeInOrder?: number; typeCode?: number }>;
  /** Total row count (best-effort; may be absent on streaming responses). */
  rowCount?: number;
  /** `true` when this page is the last one. */
  done?: boolean;
  /** Set when `done=false`; opaque id to pass to nextPage(). */
  nextBatchId?: string;
  /** Server-side request id (for support tickets / log correlation). */
  queryId?: string;
  startTime?: string;
  endTime?: string;
}

/** Metadata list response (DMOs/DLOs/CIOs combined). */
export interface SdcMetadataListResponse {
  metadata: SdcMetadataEntity[];
}

export interface SdcMetadataField {
  name: string;
  displayName?: string;
  /** SDC type — e.g. `STRING_TYPE`, `NUMBER_TYPE`, `DATE_TIME_TYPE`, `BOOLEAN_TYPE`. */
  type?: string;
  /** Indicates a primary-key-like field. */
  isPrimaryKey?: boolean;
  /** Optional business description / definition for the field. */
  description?: string;
  /** Semantic role hint: e.g. `Dimension`, `Measure`, `PrimaryKey`, `ForeignKey`. */
  category?: string;
}

export interface SdcMetadataRelationship {
  fromEntity?: string;
  toEntity?: string;
  fromEntityAttribute?: string;
  toEntityAttribute?: string;
  cardinality?: string;
  relationshipName?: string;
}

export interface SdcMetadataEntity {
  name: string;
  displayName?: string;
  /** Entity category — common values: `DataModelObject`, `DataLakeObject`, `CalculatedInsight`. */
  category?: string;
  /** Optional business description / source-system hint for the entity. */
  description?: string;
  /** When omitted on list responses; populated on describe-entity. */
  fields?: SdcMetadataField[];
  relationships?: SdcMetadataRelationship[];
  /** Some tenants expose primary keys at the entity level. */
  primaryKeys?: Array<{ name?: string; indexOrder?: string }>;
}

function normalizeTenantUrl(raw: string): string {
  const trimmed = raw.replace(/\/+$/, '');
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) return trimmed;
  return `https://${trimmed}`;
}

async function safeReadText(res: Response): Promise<string> {
  try {
    return await res.text();
  } catch {
    return '';
  }
}

function truncate(s: string, max: number): string {
  return s.length > max ? `${s.slice(0, max)}…` : s;
}
