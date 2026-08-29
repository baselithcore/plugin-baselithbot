export interface SalesforceDataCloudCredentials {
    loginUrl: string;
    apiVersion: string;
    clientId: string;
    clientSecret: string;
    dataspace?: string;
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
export declare class SalesforceDataCloudClient {
    private readonly creds;
    private session;
    /** Configurable fetch implementation — overridable for tests. */
    private readonly httpFetch;
    constructor(connectionString: string, opts?: {
        fetch?: typeof fetch;
    });
    /** Lightweight reachability probe — exchanges credentials without listing DMOs. */
    ping(): Promise<void>;
    /**
     * Submit a single SDC SQL statement. The Data Cloud Query v2 endpoint is
     * read-only by design; safety enforcement happens upstream via the SQL
     * validator before this is called.
     *
     * Pagination: if `done=false`, the server returns `nextBatchId`. Callers
     * (Executor) loop through `nextPage()` until `done` or rowLimit reached.
     */
    query(sql: string): Promise<SdcQueryPage>;
    /** Fetch the next page in a paginated query. */
    nextPage(nextBatchId: string): Promise<SdcQueryPage>;
    /**
     * List all metadata entities (DMOs / DLOs / CIOs) on the tenant.
     *
     * Salesforce Data Cloud Connect API splits versions per surface:
     *   - Metadata APIs live under `/api/v1/metadata`.
     *   - Query API lives under `/api/v2/query`.
     * Using `/api/v2/metadata` returns HTTP 404 even on a valid CDP tenant.
     */
    listEntities(): Promise<SdcMetadataListResponse>;
    /**
     * Describe a single entity by API name (returns full field list).
     *
     * Salesforce Data Cloud does not expose `/api/v1/metadata/{name}` as a path
     * — that returns HTTP 404 "No static resource". The supported shape is the
     * same list endpoint with an `entityName` query parameter, which returns a
     * `{ metadata: [entity] }` envelope containing a single fully-described entity.
     */
    describeEntity(entityName: string): Promise<SdcMetadataEntity>;
    close(): Promise<void>;
    /** Returns the parsed credentials (read-only) — useful for introspector context. */
    get credentials(): Readonly<SalesforceDataCloudCredentials>;
    private getSession;
    private invalidate;
    private fetchCoreToken;
    private exchangeForDataCloudToken;
    private request;
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
    metadata?: Record<string, {
        type: string;
        placeInOrder?: number;
        typeCode?: number;
    }>;
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
    primaryKeys?: Array<{
        name?: string;
        indexOrder?: string;
    }>;
}
//# sourceMappingURL=client.d.ts.map