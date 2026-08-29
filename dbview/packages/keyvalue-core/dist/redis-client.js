import { Redis } from 'ioredis';
/**
 * Parse `redis://[user][:pass]@host:port[/db]` (or `rediss://...`) → ioredis options.
 * Returns the configured DB index too (default 0).
 */
export function parseRedisUrl(connectionString) {
    const u = new URL(connectionString);
    const tls = u.protocol === 'rediss:';
    const port = u.port ? Number.parseInt(u.port, 10) : 6379;
    const pathDb = u.pathname.replace(/^\//, '').trim();
    const db = pathDb ? Number.parseInt(pathDb, 10) : 0;
    const options = {
        host: u.hostname,
        port,
        db: Number.isFinite(db) ? db : 0,
        username: u.username ? decodeURIComponent(u.username) : undefined,
        password: u.password ? decodeURIComponent(u.password) : undefined,
        lazyConnect: true,
        maxRetriesPerRequest: 1,
        enableReadyCheck: true,
        commandTimeout: 5_000,
        connectTimeout: 5_000,
        tls: tls ? {} : undefined,
    };
    return { options, db: options.db ?? 0 };
}
export function createRedisClient(connectionString) {
    const { options, db } = parseRedisUrl(connectionString);
    const client = new Redis(options);
    return { client, db };
}
//# sourceMappingURL=redis-client.js.map