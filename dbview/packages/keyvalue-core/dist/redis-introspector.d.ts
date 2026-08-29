import { type KeyValueStoreSchema } from '@dbview/shared';
/**
 * Introspects a Redis logical DB by streaming SCAN, classifying keys by
 * leading namespace (split on ':'), and recording observed types.
 * Bounded by MAX_KEYS_SAMPLED to keep latency predictable on large stores.
 */
export declare class RedisIntrospector {
    private readonly connectionString;
    private client;
    private dbIndex;
    constructor(connectionString: string);
    introspect(): Promise<KeyValueStoreSchema>;
    close(): Promise<void>;
}
//# sourceMappingURL=redis-introspector.d.ts.map