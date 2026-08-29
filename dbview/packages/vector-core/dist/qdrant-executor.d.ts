import type { ExecuteQueryResponse } from '@dbview/shared';
/**
 * Qdrant query executor.
 *
 * Queries are JSON envelopes describing the read operation. Supported ops:
 *
 *   {"op": "collections"}
 *   {"op": "scroll", "collection": "wiki", "limit": 50}
 *   {"op": "search", "collection": "wiki", "vector": [...], "limit": 10}
 *
 * Mutations (upsert, delete, create_collection) are blocked.
 */
export declare class QdrantExecutor {
    private readonly client;
    private readonly defaultCollection?;
    constructor(connectionString: string);
    run(query: string, rowLimit: number): Promise<ExecuteQueryResponse>;
    close(): Promise<void>;
}
//# sourceMappingURL=qdrant-executor.d.ts.map