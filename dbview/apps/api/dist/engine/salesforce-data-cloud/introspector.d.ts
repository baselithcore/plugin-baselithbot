import type { SchemaGraph } from '@dbview/shared';
import { SalesforceDataCloudClient } from './client.js';
/**
 * Salesforce Data Cloud schema introspector.
 *
 * Strategy:
 *  - GET `/api/v2/metadata` to list every entity (DMOs, DLOs, CIOs) with fields.
 *  - When the list response omits fields for some entities, fall back to
 *    per-entity describes with bounded concurrency.
 *  - Compute FK edges from declared relationships, derive each column's
 *    `isForeignKey` flag from the union of edge source columns, then build the
 *    relational SchemaGraph.
 */
export declare class SalesforceDataCloudIntrospector {
    private readonly client;
    private readonly options;
    constructor(client: SalesforceDataCloudClient, options?: {
        excludePattern?: RegExp;
        concurrency?: number;
    });
    introspect(): Promise<SchemaGraph>;
    close(): Promise<void>;
}
//# sourceMappingURL=introspector.d.ts.map