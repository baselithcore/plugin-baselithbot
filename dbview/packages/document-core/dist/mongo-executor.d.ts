import type { ExecuteQueryResponse } from '@dbview/shared';
/**
 * Read-only MongoDB executor. Accepts a JSON envelope (see safety.ts) and
 * dispatches against the connection's default DB. Results are shaped into
 * the unified columns/rows envelope.
 */
export declare class MongoExecutor {
    private readonly connectionString;
    private client;
    private database;
    constructor(connectionString: string);
    private getClient;
    run(query: string, rowLimit: number): Promise<ExecuteQueryResponse>;
    close(): Promise<void>;
}
//# sourceMappingURL=mongo-executor.d.ts.map