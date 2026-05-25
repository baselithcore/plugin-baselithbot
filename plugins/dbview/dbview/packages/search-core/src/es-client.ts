import { Client, type ClientOptions } from '@elastic/elasticsearch';

/**
 * Parse stored Elasticsearch URL into a client. Supports user:pass@ basic auth,
 * `api-key=...` query string, and `index=` default.
 */
export function parseEsUrl(connectionString: string): {
  options: ClientOptions;
  defaultIndex?: string;
} {
  const u = new URL(connectionString);
  const apiKey = u.searchParams.get('api-key') ?? undefined;
  const defaultIndex = u.searchParams.get('index') ?? undefined;
  // Reconstruct node URL without our custom query params.
  const node = `${u.protocol}//${u.host}`;
  const options: ClientOptions = {
    node,
    requestTimeout: 5_000,
    ...(u.username
      ? {
          auth: {
            username: decodeURIComponent(u.username),
            password: decodeURIComponent(u.password ?? ''),
          },
        }
      : {}),
    ...(apiKey ? { auth: { apiKey } } : {}),
  };
  return { options, defaultIndex };
}

export function createEsClient(connectionString: string): {
  client: Client;
  defaultIndex?: string;
} {
  const { options, defaultIndex } = parseEsUrl(connectionString);
  return { client: new Client(options), defaultIndex };
}
