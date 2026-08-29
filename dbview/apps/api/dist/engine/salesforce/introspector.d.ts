import type { SchemaGraph } from '@dbview/shared';
import { SalesforceClient } from './client.js';
/**
 * Salesforce schema introspector.
 *
 * Strategy:
 *  - List sObjects via `/services/data/<v>/sobjects`. Filter: queryable && !deprecated.
 *    Skip system feed/share/history junk to keep the graph readable.
 *  - Describe each kept sObject in parallel (bounded concurrency) to gather fields + lookups.
 *  - Build relational SchemaGraph: sObject → TableNode, reference field → FKEdge.
 */
export declare class SalesforceIntrospector {
    private readonly client;
    private readonly apiVersion;
    constructor(client: SalesforceClient, apiVersion: string);
    introspect(): Promise<SchemaGraph>;
    close(): Promise<void>;
}
//# sourceMappingURL=introspector.d.ts.map