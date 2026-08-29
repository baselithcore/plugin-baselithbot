import { IntrospectionError } from '@dbview/shared';
/**
 * Parse a `qdrant://` or `qdrants://` connection string.
 *
 * Format: `qdrant[s]://host:port[/collection][?api-key=<key>]`
 */
export function parseQdrantConnection(connectionString) {
    const cleaned = connectionString.trim();
    const m = /^qdrant(s?):\/\/([^/?]+)(\/[^?]*)?(\?.*)?$/.exec(cleaned);
    if (!m) {
        throw new IntrospectionError(`Invalid Qdrant connection string: ${connectionString}`);
    }
    const tls = m[1] === 's';
    const hostPort = m[2];
    const path = m[3] ?? '';
    const query = m[4] ?? '';
    const collection = path ? decodeURIComponent(path.replace(/^\/+/, '')) || undefined : undefined;
    let apiKey;
    if (query) {
        const params = new URLSearchParams(query.startsWith('?') ? query.slice(1) : query);
        const k = params.get('api-key') ?? params.get('apiKey');
        if (k)
            apiKey = k;
    }
    const scheme = tls ? 'https' : 'http';
    const baseUrl = `${scheme}://${hostPort}`;
    return { baseUrl, apiKey, collection };
}
//# sourceMappingURL=parse.js.map