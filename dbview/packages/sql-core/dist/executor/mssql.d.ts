import type { ExecuteQueryResponse } from '@dbview/shared';
import type { QueryExecutor } from './types.js';
export declare class MssqlExecutor implements QueryExecutor {
    private readonly poolPromise;
    constructor(connectionString: string);
    run(sql: string, rowLimit: number): Promise<ExecuteQueryResponse>;
    close(): Promise<void>;
}
//# sourceMappingURL=mssql.d.ts.map