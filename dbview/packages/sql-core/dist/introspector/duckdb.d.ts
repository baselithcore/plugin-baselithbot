import { type SchemaGraph } from '@dbview/shared';
import type { SchemaIntrospector } from './types.js';
export declare class DuckdbIntrospector implements SchemaIntrospector {
    private readonly filePath;
    private instance;
    private connection;
    constructor(filePath: string);
    private getConnection;
    introspect(): Promise<SchemaGraph>;
    close(): Promise<void>;
}
//# sourceMappingURL=duckdb.d.ts.map