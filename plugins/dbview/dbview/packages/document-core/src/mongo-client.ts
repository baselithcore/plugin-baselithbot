import { MongoClient, type MongoClientOptions } from 'mongodb';

/**
 * Create a MongoClient with read-friendly defaults. The connection string
 * carries auth, host, db, and any tls/authSource params. Driver-level retry
 * is disabled to fail fast.
 */
export function createMongoClient(connectionString: string): {
  client: MongoClient;
  database: string;
} {
  const options: MongoClientOptions = {
    serverSelectionTimeoutMS: 5_000,
    connectTimeoutMS: 5_000,
    socketTimeoutMS: 10_000,
    retryWrites: false,
    appName: 'dbview',
  };
  const client = new MongoClient(connectionString, options);
  // Parse default DB from URL path.
  const u = new URL(connectionString);
  const dbName = u.pathname.replace(/^\//, '') || 'test';
  return { client, database: dbName };
}
