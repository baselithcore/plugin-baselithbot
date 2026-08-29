export interface SalesforceCredentials {
    instanceUrl: string;
    apiVersion: string;
    clientId: string;
    clientSecret: string;
    isSandbox: boolean;
}
/**
 * Thin Salesforce REST client.
 *
 * Auth: OAuth 2.0 Client Credentials Flow only.
 * Connected App must have "Enable Client Credentials Flow" + a "Run As" user.
 *
 * Access tokens are kept in-memory and refreshed on demand. The token endpoint
 * returns its own `instance_url` which we honor (it may differ from the configured
 * instanceUrl when the org sits behind My Domain redirects).
 */
export declare class SalesforceClient {
    private readonly creds;
    private cached;
    constructor(connectionString: string);
    /** Get a valid access token + the instance URL to call APIs against. */
    private getToken;
    /** Invalidate cached token (use on 401). */
    private invalidate;
    /** GET an API path (e.g. `/services/data/v60.0/sobjects`). Returns parsed JSON. */
    get<T>(path: string): Promise<T>;
    /**
     * Execute a SOQL query. Honors `nextRecordsUrl` pagination up to rowLimit.
     * The caller is responsible for placing a LIMIT in the SOQL itself; pagination
     * here just stitches batched results when Salesforce splits a single LIMIT
     * into multiple pages (default 2000 records per page).
     */
    query(soql: string, rowLimit: number): Promise<SalesforceQueryRow[]>;
    /**
     * Lightweight reachability probe: hits the versioned data root, which requires
     * a valid token but does no introspection work.
     */
    ping(): Promise<void>;
    /** No persistent connection to release; method kept for QueryEngine parity. */
    close(): Promise<void>;
    private request;
}
export interface SalesforceQueryRow {
    attributes?: {
        type: string;
        url?: string;
    };
    [field: string]: unknown;
}
export interface SalesforceQueryPage {
    totalSize: number;
    done: boolean;
    nextRecordsUrl?: string;
    records: SalesforceQueryRow[];
}
//# sourceMappingURL=client.d.ts.map