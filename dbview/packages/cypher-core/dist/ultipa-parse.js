import { IntrospectionError } from '@dbview/shared';
const DEFAULT_PORT = 60061;
/**
 * Parse an `ultipa://` or `ultipas://` connection string.
 *
 * Format: `ultipa[s]://[user:pass@]host[:port][,host2[:port2],...][/graph]`
 *
 * Comma-separated hosts allowed for cluster targets.
 */
export function parseUltipaConnection(connectionString) {
    const cleaned = connectionString.trim();
    const re = /^ultipa(s?):\/\/(?:([^:@/]*)(?::([^@/]*))?@)?([^/?]+)(\/[^?]*)?(\?.*)?$/;
    const m = re.exec(cleaned);
    if (!m) {
        throw new IntrospectionError(`Invalid Ultipa connection string: ${connectionString}`);
    }
    const useSSL = m[1] === 's';
    const username = m[2] ? decodeURIComponent(m[2]) : undefined;
    const password = m[3] !== undefined ? decodeURIComponent(m[3]) : undefined;
    const hostPart = m[4];
    const path = m[5] ?? '';
    const defaultGraph = path ? decodeURIComponent(path.replace(/^\/+/, '')) || undefined : undefined;
    const hosts = hostPart
        .split(',')
        .map((h) => h.trim())
        .filter(Boolean)
        .map((h) => (h.includes(':') ? h : `${h}:${DEFAULT_PORT}`));
    if (hosts.length === 0) {
        throw new IntrospectionError(`Ultipa connection string missing host: ${connectionString}`);
    }
    return { hosts, username, password, defaultGraph, useSSL };
}
//# sourceMappingURL=ultipa-parse.js.map