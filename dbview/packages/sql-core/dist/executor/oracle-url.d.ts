import type { ConnectionAttributes } from 'oracledb';
/**
 * Parse `oracle://[user[:pass]@]host:port/serviceName[?sid=...]` into oracledb config.
 * SID query param overrides serviceName when present.
 */
export declare function parseOracleUrl(connectionString: string): ConnectionAttributes;
//# sourceMappingURL=oracle-url.d.ts.map