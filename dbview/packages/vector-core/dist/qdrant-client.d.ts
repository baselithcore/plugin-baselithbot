import type { QdrantTarget } from './parse.js';
export interface QdrantCollectionInfo {
    status: string;
    vectors_count?: number;
    points_count?: number;
    config: {
        params: {
            vectors: {
                size: number;
                distance: string;
            } | Record<string, {
                size: number;
                distance: string;
            }>;
        };
    };
}
export interface QdrantPoint {
    id: string | number;
    payload?: Record<string, unknown>;
    vector?: number[] | Record<string, number[]>;
}
/**
 * Minimal Qdrant HTTP client over `fetch`.
 *
 * Avoids depending on `@qdrant/js-client-rest` to keep the package small —
 * we only need a handful of read-only endpoints (collections list/get, scroll, search).
 */
export declare class QdrantClient {
    private readonly target;
    constructor(target: QdrantTarget);
    listCollections(): Promise<string[]>;
    getCollection(name: string): Promise<QdrantCollectionInfo>;
    countPoints(name: string, filter?: Record<string, unknown>): Promise<number>;
    scroll(name: string, limit: number, withPayload?: boolean, withVector?: boolean, filter?: Record<string, unknown>): Promise<QdrantPoint[]>;
    search(name: string, vector: number[], opts?: {
        limit?: number;
        usingNamedVector?: string;
        withPayload?: boolean;
        filter?: Record<string, unknown>;
    }): Promise<Array<{
        id: string | number;
        score: number;
        payload?: Record<string, unknown>;
    }>>;
    ping(): Promise<void>;
    private request;
}
//# sourceMappingURL=qdrant-client.d.ts.map