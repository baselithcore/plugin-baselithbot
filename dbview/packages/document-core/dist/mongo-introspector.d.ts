import { type DocumentStoreSchema } from '@dbview/shared';
export declare class MongoIntrospector {
    private readonly connectionString;
    private client;
    private database;
    constructor(connectionString: string);
    private getDb;
    introspect(): Promise<DocumentStoreSchema>;
    close(): Promise<void>;
}
//# sourceMappingURL=mongo-introspector.d.ts.map