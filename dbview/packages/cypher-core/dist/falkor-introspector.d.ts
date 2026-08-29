import { type PropertyGraphSchema } from '@dbview/shared';
export declare class FalkorIntrospector {
    private clientPromise;
    private readonly target;
    constructor(connectionString: string);
    private client;
    introspect(): Promise<PropertyGraphSchema>;
    close(): Promise<void>;
}
//# sourceMappingURL=falkor-introspector.d.ts.map