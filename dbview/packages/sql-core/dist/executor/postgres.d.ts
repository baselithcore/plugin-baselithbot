import type { ExecuteQueryResponse } from '@dbview/shared';
import type { QueryExecutor } from './types.js';
export declare class PostgresExecutor implements QueryExecutor {
    private readonly pool;
    constructor(connectionString: string);
    run(sql: string, rowLimit: number): Promise<ExecuteQueryResponse>;
    close(): Promise<void>;
}
//# sourceMappingURL=postgres.d.ts.map