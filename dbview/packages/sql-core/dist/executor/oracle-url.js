/**
 * Parse `oracle://[user[:pass]@]host:port/serviceName[?sid=...]` into oracledb config.
 * SID query param overrides serviceName when present.
 */
export function parseOracleUrl(connectionString) {
    let normalized = connectionString;
    if (normalized.startsWith('oracle://')) {
        normalized = 'http://' + normalized.slice('oracle://'.length);
    }
    const u = new URL(normalized);
    const host = u.hostname;
    const port = u.port ? Number.parseInt(u.port, 10) : 1521;
    const pathService = decodeURIComponent(u.pathname.replace(/^\//, ''));
    const sid = u.searchParams.get('sid') ?? undefined;
    const connectString = sid
        ? `${host}:${port}/${sid}`
        : pathService
            ? `${host}:${port}/${pathService}`
            : `${host}:${port}`;
    return {
        user: u.username ? decodeURIComponent(u.username) : undefined,
        password: u.password ? decodeURIComponent(u.password) : undefined,
        connectString,
    };
}
//# sourceMappingURL=oracle-url.js.map