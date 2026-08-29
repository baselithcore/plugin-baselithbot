import { type ExecuteQueryResponse } from '@dbview/shared';
/**
 * Ultipa GQL executor.
 *
 * Reuses a long-lived authenticated `GqldbClient`. The Cypher safety
 * validator runs upstream — this executor only forwards the validated GQL
 * statement with `readOnly: true` so any write attempt the validator
 * misses is still rejected server-side.
 */
export declare class UltipaExecutor {
    private clientP;
    private readonly connectionString;
    constructor(connectionString: string);
    run(query: string, rowLimit: number): Promise<ExecuteQueryResponse>;
    close(): Promise<void>;
    private connect;
}
//# sourceMappingURL=ultipa-executor.d.ts.map