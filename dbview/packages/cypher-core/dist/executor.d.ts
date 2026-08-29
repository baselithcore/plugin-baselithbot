import type { ExecuteQueryResponse } from '@dbview/shared';
export declare class Neo4jExecutor {
    private readonly driver;
    constructor(connectionString: string);
    run(query: string, rowLimit: number): Promise<ExecuteQueryResponse>;
    close(): Promise<void>;
}
//# sourceMappingURL=executor.d.ts.map