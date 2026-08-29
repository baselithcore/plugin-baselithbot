import type { ExecuteQueryResponse } from '@dbview/shared';
import type { QueryExecutor } from './types.js';
export declare class SqliteExecutor implements QueryExecutor {
    private readonly db;
    constructor(filePath: string);
    run(sql: string, rowLimit: number): Promise<ExecuteQueryResponse>;
    close(): Promise<void>;
}
//# sourceMappingURL=sqlite.d.ts.map