import { type PropertyGraphSchema } from '@dbview/shared';
export declare class Neo4jIntrospector {
    private readonly driver;
    constructor(connectionString: string);
    introspect(): Promise<PropertyGraphSchema>;
    private attachLabelSamples;
    private attachRelSamples;
    private collectLabels;
    private collectRelationships;
    close(): Promise<void>;
}
//# sourceMappingURL=introspector.d.ts.map