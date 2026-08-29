import { parseSalesforceDataCloudConnection } from '@dbview/shared';
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
    creds;
    session = null;
    /** Configurable fetch implementation — overridable for tests. */
    httpFetch;
    constructor(connectionString, opts) {
        this.creds = parseSalesforceDataCloudConnection(connectionString);
        this.httpFetch = opts?.fetch ?? fetch;
    }
    /** Lightweight reachability probe — exchanges credentials without listing DMOs. */
    async ping() {
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
    async query(sql) {
        return this.request('POST', '/api/v2/query', { sql });
    }
    /** Fetch the next page in a paginated query. */
    async nextPage(nextBatchId) {
        if (!/^[A-Za-z0-9_-]+$/.test(nextBatchId)) {
            throw new Error('Invalid nextBatchId.');
        }
        return this.request('GET', `/api/v2/query/${nextBatchId}`);
    }
    /**
     * List all metadata entities (DMOs / DLOs / CIOs) on the tenant.
     *
     * Salesforce Data Cloud Connect API splits versions per surface:
     *   - Metadata APIs live under `/api/v1/metadata`.
     *   - Query API lives under `/api/v2/query`.
     * Using `/api/v2/metadata` returns HTTP 404 even on a valid CDP tenant.
     */
    async listEntities() {
        return this.request('GET', '/api/v1/metadata');
    }
    /**
     * Describe a single entity by API name (returns full field list).
     *
     * Salesforce Data Cloud does not expose `/api/v1/metadata/{name}` as a path
     * — that returns HTTP 404 "No static resource". The supported shape is the
     * same list endpoint with an `entityName` query parameter, which returns a
     * `{ metadata: [entity] }` envelope containing a single fully-described entity.
     */
    async describeEntity(entityName) {
        if (!/^[A-Za-z0-9_]+$/.test(entityName)) {
            throw new Error(`Invalid entity name: ${entityName}`);
        }
        const wrapped = await this.request('GET', `/api/v1/metadata?entityName=${encodeURIComponent(entityName)}`);
        const first = wrapped.metadata?.[0];
        if (!first) {
            throw new Error(`Data Cloud metadata for '${entityName}' returned no entities.`);
        }
        return first;
    }
    async close() {
        this.session = null;
    }
    /** Returns the parsed credentials (read-only) — useful for introspector context. */
    get credentials() {
        return this.creds;
    }
    async getSession() {
        if (this.session && Date.now() < this.session.refreshAt)
            return this.session;
        const core = await this.fetchCoreToken();
        const cdp = await this.exchangeForDataCloudToken(core);
        this.session = cdp;
        return cdp;
    }
    invalidate() {
        this.session = null;
    }
    async fetchCoreToken() {
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
            throw new Error(`Salesforce core auth failed (${res.status}): ${truncate(text, 240) || res.statusText}`);
        }
        const data = (await res.json());
        if (!data.access_token || !data.instance_url) {
            throw new Error('Salesforce core auth response missing access_token or instance_url');
        }
        return {
            token: data.access_token,
            instanceUrl: data.instance_url.replace(/\/+$/, ''),
        };
    }
    async exchangeForDataCloudToken(core) {
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
            throw new Error(`Salesforce Data Cloud token exchange failed (${res.status}): ${truncate(text, 240) || res.statusText}`);
        }
        const data = (await res.json());
        if (!data.access_token || !data.instance_url) {
            throw new Error('Data Cloud token exchange response missing access_token or instance_url');
        }
        const ttlSec = typeof data.expires_in === 'number' && data.expires_in > 60 ? data.expires_in : 1800;
        const tenantUrl = normalizeTenantUrl(data.instance_url);
        return {
            cdpToken: data.access_token,
            tenantUrl,
            refreshAt: Date.now() + (ttlSec - 60) * 1000,
        };
    }
    async request(method, path, body, _retried = false) {
        const session = await this.getSession();
        const url = path.startsWith('http') ? path : `${session.tenantUrl}${path}`;
        const headers = {
            Authorization: `Bearer ${session.cdpToken}`,
            Accept: 'application/json',
        };
        let payload;
        if (body !== undefined) {
            headers['Content-Type'] = 'application/json';
            payload = JSON.stringify(body);
        }
        const res = await this.httpFetch(url, { method, headers, body: payload });
        if (res.status === 401 && !_retried) {
            this.invalidate();
            return this.request(method, path, body, true);
        }
        if (!res.ok) {
            const text = await safeReadText(res);
            throw new Error(`Salesforce Data Cloud ${method} ${path} failed (${res.status}): ${truncate(text, 320) || res.statusText}`);
        }
        return (await res.json());
    }
}
function normalizeTenantUrl(raw) {
    const trimmed = raw.replace(/\/+$/, '');
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://'))
        return trimmed;
    return `https://${trimmed}`;
}
async function safeReadText(res) {
    try {
        return await res.text();
    }
    catch {
        return '';
    }
}
function truncate(s, max) {
    return s.length > max ? `${s.slice(0, max)}…` : s;
}
//# sourceMappingURL=client.js.map