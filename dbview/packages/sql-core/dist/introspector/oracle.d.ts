import { type SchemaGraph } from '@dbview/shared';
import type { SchemaIntrospector } from './types.js';
export declare class OracleIntrospector implements SchemaIntrospector {
    private readonly cfg;
    private pool;
    constructor(connectionString: string);
    private getPool;
    introspect(): Promise<SchemaGraph>;
    close(): Promise<void>;
}
//# sourceMappingURL=oracle.d.ts.map