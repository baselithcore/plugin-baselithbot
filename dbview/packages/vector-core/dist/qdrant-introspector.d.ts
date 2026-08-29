import type { VectorStoreSchema } from '@dbview/shared';
export declare class QdrantIntrospector {
    private readonly client;
    private readonly collectionFilter?;
    constructor(connectionString: string);
    introspect(): Promise<VectorStoreSchema>;
    close(): Promise<void>;
}
//# sourceMappingURL=qdrant-introspector.d.ts.map