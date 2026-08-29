import { type Dialect, type ExecuteQueryResponse, type UnifiedSchema } from '@dbview/shared';
export interface QueryEngine {
    introspect(): Promise<UnifiedSchema>;
    execute(query: string, rowLimit: number): Promise<ExecuteQueryResponse>;
    close(): Promise<void>;
    /**
     * Optional lightweight reachability probe. When implemented, callers should
     * prefer it over `introspect()` for connection-test paths (avoids paying full
     * introspection cost for engines like Salesforce that describe every sObject).
     */
    verifyReachable?(): Promise<void>;
}
export declare function createQueryEngine(dialect: Dialect, connectionString: string): QueryEngine;
//# sourceMappingURL=factory.d.ts.map