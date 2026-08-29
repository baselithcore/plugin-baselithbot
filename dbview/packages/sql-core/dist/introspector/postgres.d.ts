import { type SchemaGraph } from '@dbview/shared';
import type { SchemaIntrospector } from './types.js';
type PostgresWireDialect = 'postgres' | 'cockroach';
export declare class PostgresIntrospector implements SchemaIntrospector {
    private readonly pool;
    private readonly dialect;
    constructor(connectionString: string, dialect?: PostgresWireDialect);
    introspect(): Promise<SchemaGraph>;
    close(): Promise<void>;
}
export {};
//# sourceMappingURL=postgres.d.ts.map