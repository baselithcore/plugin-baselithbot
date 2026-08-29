import { IntrospectionError } from '@dbview/shared';
const REQUEST_TIMEOUT_MS = 15_000;
/**
 * Minimal Qdrant HTTP client over `fetch`.
 *
 * Avoids depending on `@qdrant/js-client-rest` to keep the package small —
 * we only need a handful of read-only endpoints (collections list/get, scroll, search).
 */
export class QdrantClient {
    target;
    constructor(target) {
        this.target = target;
    }
    async listCollections() {
        const res = await this.request('GET', '/collections');
        return res.result.collections.map((c) => c.name);
    }
    async getCollection(name) {
        const res = await this.request('GET', `/collections/${encodeURIComponent(name)}`);
        return res.result;
    }
    async countPoints(name, filter) {
        const body = { exact: true };
        if (filter)
            body.filter = filter;
        const res = await this.request('POST', `/collections/${encodeURIComponent(name)}/points/count`, body);
        return res.result.count;
    }
    async scroll(name, limit, withPayload = true, withVector = false, filter) {
        const body = {
            limit,
            with_payload: withPayload,
            with_vector: withVector,
        };
        if (filter)
            body.filter = filter;
        const res = await this.request('POST', `/collections/${encodeURIComponent(name)}/points/scroll`, body);
        return res.result.points ?? [];
    }
    async search(name, vector, opts = {}) {
        const body = {
            vector: opts.usingNamedVector ? { name: opts.usingNamedVector, vector } : vector,
            limit: opts.limit ?? 20,
            with_payload: opts.withPayload ?? true,
        };
        if (opts.filter)
            body.filter = opts.filter;
        const res = await this.request('POST', `/collections/${encodeURIComponent(name)}/points/search`, body);
        return res.result;
    }
    async ping() {
        // `/healthz` is the lightweight readiness check exposed by recent Qdrant versions.
        // Fall back to listing collections if that endpoint is missing.
        try {
            await this.request('GET', '/healthz');
        }
        catch {
            await this.listCollections();
        }
    }
    async request(method, path, body) {
        const url = `${this.target.baseUrl}${path}`;
        const headers = { 'content-type': 'application/json' };
        if (this.target.apiKey)
            headers['api-key'] = this.target.apiKey;
        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), REQUEST_TIMEOUT_MS);
        try {
            const res = await fetch(url, {
                method,
                headers,
                body: body !== undefined ? JSON.stringify(body) : undefined,
                signal: ctrl.signal,
            });
            const text = await res.text();
            if (!res.ok) {
                throw new IntrospectionError(`Qdrant ${method} ${path} → ${res.status}: ${text.slice(0, 200) || res.statusText}`);
            }
            if (!text)
                return {};
            return JSON.parse(text);
        }
        catch (err) {
            if (err.name === 'AbortError') {
                throw new IntrospectionError(`Qdrant ${method} ${path} timed out after ${REQUEST_TIMEOUT_MS}ms`);
            }
            if (err instanceof IntrospectionError)
                throw err;
            throw new IntrospectionError(`Qdrant ${method} ${path} failed: ${err.message}`);
        }
        finally {
            clearTimeout(timer);
        }
    }
}
//# sourceMappingURL=qdrant-client.js.map