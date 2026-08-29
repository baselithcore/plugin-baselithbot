import type { ExecuteQueryResponse } from '@dbview/shared';
/**
 * Executes a read-only Elasticsearch envelope.
 * The envelope is a JSON object describing the op (see safety.ts).
 * Output is shaped into the unified columns/rows response.
 */
export declare class ElasticsearchExecutor {
    private readonly connectionString;
    private client;
    constructor(connectionString: string);
    private getClient;
    run(query: string, rowLimit: number): Promise<ExecuteQueryResponse>;
    close(): Promise<void>;
}
//# sourceMappingURL=es-executor.d.ts.map