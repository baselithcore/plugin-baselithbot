import { IntrospectionError, } from '@dbview/shared';
import { createRedisClient } from './redis-client.js';
const MAX_KEYS_SAMPLED = 5_000;
const SCAN_BATCH = 500;
const SAMPLE_KEYS_PER_NAMESPACE = 6;
/**
 * Introspects a Redis logical DB by streaming SCAN, classifying keys by
 * leading namespace (split on ':'), and recording observed types.
 * Bounded by MAX_KEYS_SAMPLED to keep latency predictable on large stores.
 */
export class RedisIntrospector {
    connectionString;
    client;
    dbIndex;
    constructor(connectionString) {
        this.connectionString = connectionString;
        const { client, db } = createRedisClient(connectionString);
        this.client = client;
        this.dbIndex = db;
    }
    async introspect() {
        const client = this.client;
        if (!client)
            throw new IntrospectionError('Redis client not initialized.');
        try {
            if (client.status === 'wait' || client.status === 'end') {
                await client.connect();
            }
            const keys = [];
            let cursor = '0';
            do {
                const [next, batch] = (await client.scan(cursor, 'COUNT', SCAN_BATCH));
                keys.push(...batch);
                cursor = next;
                if (keys.length >= MAX_KEYS_SAMPLED)
                    break;
            } while (cursor !== '0');
            const grouped = new Map();
            for (const k of keys) {
                const prefix = k.includes(':') ? `${k.split(':')[0]}:*` : '(no-prefix)';
                let g = grouped.get(prefix);
                if (!g) {
                    g = { types: new Set(), samples: [], count: 0 };
                    grouped.set(prefix, g);
                }
                g.count += 1;
                if (g.samples.length < SAMPLE_KEYS_PER_NAMESPACE)
                    g.samples.push(k);
            }
            const typeProbes = [];
            for (const [prefix, g] of grouped) {
                for (const key of g.samples)
                    typeProbes.push({ prefix, key });
            }
            if (typeProbes.length) {
                const pipeline = client.pipeline();
                for (const p of typeProbes)
                    pipeline.type(p.key);
                const runPipeline = pipeline['exec'];
                const results = (await runPipeline.call(pipeline)) ?? [];
                results.forEach((res, idx) => {
                    const t = res?.[1];
                    const probe = typeProbes[idx];
                    if (t && probe)
                        grouped.get(probe.prefix)?.types.add(t);
                });
            }
            const namespaces = [...grouped.entries()]
                .map(([pattern, g]) => ({
                pattern,
                types: [...g.types].sort(),
                sampleKeys: g.samples,
                keyCount: g.count,
            }))
                .sort((a, b) => b.keyCount - a.keyCount);
            return {
                kind: 'keyvalue',
                dialect: 'redis',
                db: this.dbIndex,
                totalKeys: keys.length,
                namespaces,
                generatedAt: new Date().toISOString(),
            };
        }
        catch (err) {
            throw new IntrospectionError(`Redis introspection failed: ${err.message ?? String(err)}`);
        }
    }
    async close() {
        if (this.client) {
            await this.client.quit().catch(() => undefined);
            this.client = undefined;
        }
    }
}
//# sourceMappingURL=redis-introspector.js.map