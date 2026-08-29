import { type SchemaGraph } from '@dbview/shared';
import type { SchemaIntrospector } from './types.js';
export declare class SqliteIntrospector implements SchemaIntrospector {
    private readonly db;
    constructor(filePath: string);
    introspect(): Promise<SchemaGraph>;
    close(): Promise<void>;
}
//# sourceMappingURL=sqlite.d.ts.map