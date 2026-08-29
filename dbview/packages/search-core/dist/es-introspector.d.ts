import { type SearchStoreSchema } from '@dbview/shared';
export declare class ElasticsearchIntrospector {
    private readonly connectionString;
    private client;
    constructor(connectionString: string);
    private getClient;
    introspect(): Promise<SearchStoreSchema>;
    close(): Promise<void>;
}
//# sourceMappingURL=es-introspector.d.ts.map