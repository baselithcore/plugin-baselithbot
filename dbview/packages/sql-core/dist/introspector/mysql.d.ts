import { type SchemaGraph, type SqlDialect } from '@dbview/shared';
import type { SchemaIntrospector } from './types.js';
export declare class MysqlIntrospector implements SchemaIntrospector {
    private readonly dialect;
    private readonly pool;
    constructor(connectionString: string, dialect?: SqlDialect);
    introspect(): Promise<SchemaGraph>;
    close(): Promise<void>;
}
//# sourceMappingURL=mysql.d.ts.map