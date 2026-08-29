import type { ExecuteQueryResponse } from '@dbview/shared';
import type { SalesforceClient } from './client.js';
/**
 * Salesforce SOQL executor. The caller is expected to pass an already-validated
 * SOQL query (see SalesforceSafetyValidator). This module only performs
 * execution + result projection, no extra safety enforcement.
 */
export declare class SalesforceExecutor {
    private readonly client;
    constructor(client: SalesforceClient);
    run(soql: string, rowLimit: number): Promise<ExecuteQueryResponse>;
    close(): Promise<void>;
}
//# sourceMappingURL=executor.d.ts.map