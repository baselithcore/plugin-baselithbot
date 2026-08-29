import { type PropertyGraphSchema } from '@dbview/shared';
export declare class UltipaIntrospector {
    private clientP;
    private readonly connectionString;
    constructor(connectionString: string);
    introspect(): Promise<PropertyGraphSchema>;
    private fetchNodeTypes;
    private fetchEdgeTypes;
    close(): Promise<void>;
    private connect;
    private discoverRelationships;
}
//# sourceMappingURL=ultipa-introspector.d.ts.map