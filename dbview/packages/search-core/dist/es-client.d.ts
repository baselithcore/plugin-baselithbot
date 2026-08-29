import { Client, type ClientOptions } from '@elastic/elasticsearch';
/**
 * Parse stored Elasticsearch URL into a client. Supports user:pass@ basic auth,
 * `api-key=...` query string, and `index=` default.
 */
export declare function parseEsUrl(connectionString: string): {
    options: ClientOptions;
    defaultIndex?: string;
};
export declare function createEsClient(connectionString: string): {
    client: Client;
    defaultIndex?: string;
};
//# sourceMappingURL=es-client.d.ts.map