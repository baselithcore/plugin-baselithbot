import { describe, expect, it } from 'vitest';
import { SalesforceDataCloudClient } from './client.js';

const CONN_STRING = [
  'salesforce-data-cloud://?',
  'loginUrl=https%3A%2F%2Facme.my.salesforce.com&',
  'apiVersion=v60.0&',
  'clientId=cid&',
  'clientSecret=secret',
].join('');

function makeResponse(body: unknown, init?: { status?: number; statusText?: string }): Response {
  return new Response(JSON.stringify(body), {
    status: init?.status ?? 200,
    statusText: init?.statusText ?? 'OK',
    headers: { 'Content-Type': 'application/json' },
  });
}

interface FetchCall {
  url: string;
  init: RequestInit | undefined;
}

function makeFetch(handlers: Array<(call: FetchCall) => Response | Promise<Response>>): {
  fetch: typeof fetch;
  calls: FetchCall[];
} {
  const calls: FetchCall[] = [];
  const queue = [...handlers];
  const fn = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString();
    calls.push({ url, init });
    const h = queue.shift();
    if (!h) throw new Error(`Unexpected fetch call to ${url}`);
    return h({ url, init });
  }) as typeof fetch;
  return { fetch: fn, calls };
}

describe('SalesforceDataCloudClient', () => {
  it('exchanges core token for CDP token and calls /api/v2/query', async () => {
    const { fetch: f, calls } = makeFetch([
      () =>
        makeResponse({
          access_token: 'core-tok',
          instance_url: 'https://acme.my.salesforce.com',
        }),
      () =>
        makeResponse({
          access_token: 'cdp-tok',
          instance_url: 'https://acme.c360a.salesforce.com',
          expires_in: 3600,
        }),
      () =>
        makeResponse({
          data: [{ Id: '1', Name: 'A' }],
          metadata: {
            Id: { type: 'STRING_TYPE', placeInOrder: 0 },
            Name: { type: 'STRING_TYPE', placeInOrder: 1 },
          },
          done: true,
        }),
    ]);

    const client = new SalesforceDataCloudClient(CONN_STRING, { fetch: f });
    const page = await client.query('SELECT Id, Name FROM Account__dlm LIMIT 1');

    expect(page.data).toEqual([{ Id: '1', Name: 'A' }]);
    expect(calls).toHaveLength(3);
    expect(calls[0]!.url).toBe('https://acme.my.salesforce.com/services/oauth2/token');
    expect(calls[1]!.url).toBe('https://acme.my.salesforce.com/services/a360/token');
    expect(calls[2]!.url).toBe('https://acme.c360a.salesforce.com/api/v2/query');
    const queryInit = calls[2]!.init!;
    expect(queryInit.method).toBe('POST');
    const queryHeaders = queryInit.headers as Record<string, string>;
    expect(queryHeaders.Authorization).toBe('Bearer cdp-tok');
    expect(queryHeaders['Content-Type']).toBe('application/json');
    expect(queryInit.body).toBe(
      JSON.stringify({ sql: 'SELECT Id, Name FROM Account__dlm LIMIT 1' })
    );
  });

  it('caches session across calls and only re-auths after expiry', async () => {
    const { fetch: f, calls } = makeFetch([
      () => makeResponse({ access_token: 'core', instance_url: 'https://acme.my.salesforce.com' }),
      () =>
        makeResponse({
          access_token: 'cdp',
          instance_url: 'https://acme.c360a.salesforce.com',
          expires_in: 3600,
        }),
      () => makeResponse({ data: [], done: true }),
      () => makeResponse({ data: [], done: true }),
    ]);
    const client = new SalesforceDataCloudClient(CONN_STRING, { fetch: f });
    await client.query('SELECT 1');
    await client.query('SELECT 2');
    expect(calls.map((c) => c.url)).toEqual([
      'https://acme.my.salesforce.com/services/oauth2/token',
      'https://acme.my.salesforce.com/services/a360/token',
      'https://acme.c360a.salesforce.com/api/v2/query',
      'https://acme.c360a.salesforce.com/api/v2/query',
    ]);
  });

  it('retries once on 401 by re-authenticating', async () => {
    const { fetch: f, calls } = makeFetch([
      () => makeResponse({ access_token: 'core1', instance_url: 'https://acme.my.salesforce.com' }),
      () =>
        makeResponse({
          access_token: 'cdp1',
          instance_url: 'https://acme.c360a.salesforce.com',
          expires_in: 3600,
        }),
      () => new Response('expired', { status: 401, statusText: 'Unauthorized' }),
      () => makeResponse({ access_token: 'core2', instance_url: 'https://acme.my.salesforce.com' }),
      () =>
        makeResponse({
          access_token: 'cdp2',
          instance_url: 'https://acme.c360a.salesforce.com',
          expires_in: 3600,
        }),
      () => makeResponse({ data: [{ Id: 'ok' }], done: true }),
    ]);
    const client = new SalesforceDataCloudClient(CONN_STRING, { fetch: f });
    const page = await client.query('SELECT Id FROM X__dlm');
    expect(page.data).toEqual([{ Id: 'ok' }]);
    // Final query call must use the refreshed cdp token.
    const lastCall = calls.at(-1)!;
    const headers = lastCall.init!.headers as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer cdp2');
  });

  it('forwards dataspace into the token-exchange body when configured', async () => {
    const csWithDataspace = `${CONN_STRING}&dataspace=brand_a`;
    const { fetch: f, calls } = makeFetch([
      () => makeResponse({ access_token: 'core', instance_url: 'https://acme.my.salesforce.com' }),
      () =>
        makeResponse({
          access_token: 'cdp',
          instance_url: 'https://acme.c360a.salesforce.com',
          expires_in: 3600,
        }),
      () => makeResponse({ data: [], done: true }),
    ]);
    const client = new SalesforceDataCloudClient(csWithDataspace, { fetch: f });
    await client.ping();
    const exchangeCall = calls[1]!;
    const body = String(exchangeCall.init!.body);
    expect(body).toContain('dataspace=brand_a');
  });

  it('throws a descriptive error when core auth fails', async () => {
    const { fetch: f } = makeFetch([
      () => new Response('bad client', { status: 400, statusText: 'Bad Request' }),
    ]);
    const client = new SalesforceDataCloudClient(CONN_STRING, { fetch: f });
    await expect(client.query('SELECT 1')).rejects.toThrow(/core auth failed/i);
  });

  it('rejects malformed nextBatchId', async () => {
    const { fetch: f } = makeFetch([]);
    const client = new SalesforceDataCloudClient(CONN_STRING, { fetch: f });
    await expect(client.nextPage('../escape')).rejects.toThrow(/Invalid nextBatchId/);
  });
});
