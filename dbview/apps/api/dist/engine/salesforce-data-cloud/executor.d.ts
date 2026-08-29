import type { ExecuteQueryResponse } from '@dbview/shared';
import type { SalesforceDataCloudClient } from './client.js';
/**
 * Salesforce Data Cloud query executor.
 *
 * `/api/v2/query` response shape (current Connect API):
 *   {
 *     data:     unknown[][],                          // positional row arrays
 *     metadata: { [col]: { type, placeInOrder, ... }} // col → array index
 *     done:     boolean,
 *     nextBatchId?: string,
 *     rowCount?: number,
 *     ...
 *   }
 *
 * Legacy v1 endpoints — and a handful of edge cases on v2 — emit rows as
 * objects keyed by column name. We handle both shapes by detecting whether
 * the first row is an Array (positional) or an Object (keyed).
 *
 * Pagination: when `done=false`, the server returns `nextBatchId`. We loop
 * through `nextPage()` until `done` or `rowLimit` is reached.
 */
export declare class SalesforceDataCloudExecutor {
    private readonly client;
    constructor(client: SalesforceDataCloudClient);
    run(sql: string, rowLimit: number): Promise<ExecuteQueryResponse>;
    close(): Promise<void>;
}
//# sourceMappingURL=executor.d.ts.map