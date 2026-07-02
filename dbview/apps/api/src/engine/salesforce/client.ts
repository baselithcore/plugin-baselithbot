import { parseSalesforceConnection } from '@dbview/shared';

export interface SalesforceCredentials {
  instanceUrl: string;
  apiVersion: string;
  clientId: string;
  clientSecret: string;
  isSandbox: boolean;
}

interface AccessToken {
  token: string;
  /** Epoch ms when we should refresh (we refresh ~30s before issuer expiry). */
  refreshAt: number;
  /** Instance URL returned by the token endpoint — authoritative for API calls. */
  resolvedInstanceUrl: string;
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
export class SalesforceClient {
  private readonly creds: SalesforceCredentials;
  private cached: AccessToken | null = null;

  constructor(connectionString: string) {
    const parsed = parseSalesforceConnection(connectionString);
    this.creds = parsed;
  }

  /** Get a valid access token + the instance URL to call APIs against. */
  private async getToken(): Promise<AccessToken> {
    if (this.cached && Date.now() < this.cached.refreshAt) return this.cached;
    const tokenUrl = `${this.creds.instanceUrl.replace(/\/+$/, '')}/services/oauth2/token`;
    const body = new URLSearchParams({
      grant_type: 'client_credentials',
      client_id: this.creds.clientId,
      client_secret: this.creds.clientSecret,
    });
    const res = await fetch(tokenUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    });
    if (!res.ok) {
      const text = await safeReadText(res);
      throw new Error(
        `Salesforce auth failed (${res.status}): ${truncate(text, 240) || res.statusText}`,
      );
    }
    const data = (await res.json()) as {
      access_token?: string;
      instance_url?: string;
      // Salesforce returns expires_in only on some flows; client_credentials uses Connected App TTL.
      // Default to a conservative 25-minute cache.
    };
    if (!data.access_token || !data.instance_url) {
      throw new Error('Salesforce auth response missing access_token or instance_url');
    }
    const refreshAt = Date.now() + 25 * 60 * 1000;
    this.cached = {
      token: data.access_token,
      refreshAt,
      resolvedInstanceUrl: data.instance_url.replace(/\/+$/, ''),
    };
    return this.cached;
  }

  /** Invalidate cached token (use on 401). */
  private invalidate(): void {
    this.cached = null;
  }

  /** GET an API path (e.g. `/services/data/v60.0/sobjects`). Returns parsed JSON. */
  async get<T>(path: string): Promise<T> {
    return this.request<T>('GET', path);
  }

  /**
   * Execute a SOQL query. Honors `nextRecordsUrl` pagination up to rowLimit.
   * The caller is responsible for placing a LIMIT in the SOQL itself; pagination
   * here just stitches batched results when Salesforce splits a single LIMIT
   * into multiple pages (default 2000 records per page).
   */
  async query(soql: string, rowLimit: number): Promise<SalesforceQueryRow[]> {
    const path = `/services/data/${this.creds.apiVersion}/query?q=${encodeURIComponent(soql)}`;
    let page = await this.get<SalesforceQueryPage>(path);
    const rows: SalesforceQueryRow[] = [...page.records];
    while (!page.done && rows.length < rowLimit && page.nextRecordsUrl) {
      page = await this.get<SalesforceQueryPage>(page.nextRecordsUrl);
      rows.push(...page.records);
    }
    return rows.slice(0, rowLimit);
  }

  /**
   * Lightweight reachability probe: hits the versioned data root, which requires
   * a valid token but does no introspection work.
   */
  async ping(): Promise<void> {
    await this.get<unknown>(`/services/data/${this.creds.apiVersion}/`);
  }

  /** No persistent connection to release; method kept for QueryEngine parity. */
  async close(): Promise<void> {
    this.cached = null;
  }

  private async request<T>(method: 'GET', path: string, _retried = false): Promise<T> {
    const tok = await this.getToken();
    const url = path.startsWith('http') ? path : `${tok.resolvedInstanceUrl}${path}`;
    const res = await fetch(url, {
      method,
      headers: {
        Authorization: `Bearer ${tok.token}`,
        Accept: 'application/json',
      },
    });
    if (res.status === 401 && !_retried) {
      this.invalidate();
      return this.request<T>(method, path, true);
    }
    if (!res.ok) {
      const text = await safeReadText(res);
      throw new Error(
        `Salesforce ${method} ${path} failed (${res.status}): ${truncate(text, 240) || res.statusText}`,
      );
    }
    return (await res.json()) as T;
  }
}

export interface SalesforceQueryRow {
  attributes?: { type: string; url?: string };
  [field: string]: unknown;
}

export interface SalesforceQueryPage {
  totalSize: number;
  done: boolean;
  nextRecordsUrl?: string;
  records: SalesforceQueryRow[];
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
