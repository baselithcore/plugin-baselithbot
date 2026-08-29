import type { ExecuteQueryResponse } from '@dbview/shared';
import type { QueryExecutor } from './types.js';
export declare class OracleExecutor implements QueryExecutor {
    private readonly cfg;
    private pool;
    constructor(connectionString: string);
    private getPool;
    run(sql: string, rowLimit: number): Promise<ExecuteQueryResponse>;
    close(): Promise<void>;
}
//# sourceMappingURL=oracle.d.ts.map