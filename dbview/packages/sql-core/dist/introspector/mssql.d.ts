import { type SchemaGraph } from '@dbview/shared';
import type { SchemaIntrospector } from './types.js';
export declare class MssqlIntrospector implements SchemaIntrospector {
    private readonly poolPromise;
    constructor(connectionString: string);
    introspect(): Promise<SchemaGraph>;
    close(): Promise<void>;
}
//# sourceMappingURL=mssql.d.ts.map