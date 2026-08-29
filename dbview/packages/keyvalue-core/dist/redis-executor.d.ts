import type { ExecuteQueryResponse } from '@dbview/shared';
/**
 * Executes a single read-only Redis command. Input is a plain Redis CLI line
 * (e.g. `HGETALL user:1` or `SCAN 0 MATCH user:* COUNT 100`).
 * Response is shaped into the unified columns/rows envelope so the UI can render
 * tabularly, regardless of native Redis reply type.
 */
export declare class RedisExecutor {
    private readonly connectionString;
    private client;
    constructor(connectionString: string);
    private getClient;
    run(query: string, rowLimit: number): Promise<ExecuteQueryResponse>;
    close(): Promise<void>;
}
//# sourceMappingURL=redis-executor.d.ts.map