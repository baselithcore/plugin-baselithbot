import type { ExecuteQueryResponse } from '@dbview/shared';
import type { QueryExecutor } from './types.js';
export declare class ClickhouseExecutor implements QueryExecutor {
    private readonly connectionString;
    private client;
    constructor(connectionString: string);
    private getClient;
    run(sql: string, rowLimit: number): Promise<ExecuteQueryResponse>;
    close(): Promise<void>;
}
//# sourceMappingURL=clickhouse.d.ts.map