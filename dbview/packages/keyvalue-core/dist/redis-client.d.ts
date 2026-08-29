import type { Redis as RedisClient, RedisOptions } from 'ioredis';
/**
 * Parse `redis://[user][:pass]@host:port[/db]` (or `rediss://...`) → ioredis options.
 * Returns the configured DB index too (default 0).
 */
export declare function parseRedisUrl(connectionString: string): {
    options: RedisOptions;
    db: number;
};
export declare function createRedisClient(connectionString: string): {
    client: RedisClient;
    db: number;
};
//# sourceMappingURL=redis-client.d.ts.map