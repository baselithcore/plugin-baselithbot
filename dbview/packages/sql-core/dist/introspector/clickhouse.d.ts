import { type SchemaGraph } from '@dbview/shared';
import type { SchemaIntrospector } from './types.js';
export declare class ClickhouseIntrospector implements SchemaIntrospector {
    private readonly connectionString;
    private client;
    constructor(connectionString: string);
    private getClient;
    introspect(): Promise<SchemaGraph>;
    close(): Promise<void>;
}
//# sourceMappingURL=clickhouse.d.ts.map