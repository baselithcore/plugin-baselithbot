export interface UltipaTarget {
    hosts: string[];
    username?: string;
    password?: string;
    defaultGraph?: string;
    useSSL: boolean;
}
/**
 * Parse an `ultipa://` or `ultipas://` connection string.
 *
 * Format: `ultipa[s]://[user:pass@]host[:port][,host2[:port2],...][/graph]`
 *
 * Comma-separated hosts allowed for cluster targets.
 */
export declare function parseUltipaConnection(connectionString: string): UltipaTarget;
//# sourceMappingURL=ultipa-parse.d.ts.map