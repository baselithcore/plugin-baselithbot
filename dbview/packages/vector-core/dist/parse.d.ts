export interface QdrantTarget {
    baseUrl: string;
    apiKey?: string;
    collection?: string;
}
/**
 * Parse a `qdrant://` or `qdrants://` connection string.
 *
 * Format: `qdrant[s]://host:port[/collection][?api-key=<key>]`
 */
export declare function parseQdrantConnection(connectionString: string): QdrantTarget;
//# sourceMappingURL=parse.d.ts.map