import { type FalkorDBOptions } from 'falkordb';
import type { ExecuteQueryResponse } from '@dbview/shared';
interface FalkorTarget {
    options: FalkorDBOptions;
    graphName: string;
}
/**
 * Connection string: `falkor://[user]:[pass]@host:port/graphName`
 * Falls back to `redis://` scheme. graphName from URL path.
 */
export declare function parseFalkorConnection(connectionString: string): FalkorTarget;
export declare class FalkorExecutor {
    private clientPromise;
    private readonly target;
    constructor(connectionString: string);
    private client;
    run(query: string, rowLimit: number): Promise<ExecuteQueryResponse>;
    close(): Promise<void>;
}
export {};
//# sourceMappingURL=falkor-executor.d.ts.map