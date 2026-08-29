import { MongoClient } from 'mongodb';
/**
 * Create a MongoClient with read-friendly defaults. The connection string
 * carries auth, host, db, and any tls/authSource params. Driver-level retry
 * is disabled to fail fast.
 */
export declare function createMongoClient(connectionString: string): {
    client: MongoClient;
    database: string;
};
//# sourceMappingURL=mongo-client.d.ts.map