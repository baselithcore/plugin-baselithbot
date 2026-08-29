import type { ExecuteQueryResponse } from '@dbview/shared';
import type { QueryExecutor } from './types.js';
export declare class DuckdbExecutor implements QueryExecutor {
    private readonly filePath;
    private instance;
    private connection;
    constructor(filePath: string);
    private getConnection;
    run(sql: string, rowLimit: number): Promise<ExecuteQueryResponse>;
    close(): Promise<void>;
}
//# sourceMappingURL=duckdb.d.ts.map