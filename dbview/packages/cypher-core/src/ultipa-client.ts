import { ConfigBuilder, GqldbClient } from '@ultipa-graph/ultipa-driver';
import { parseUltipaConnection, type UltipaTarget } from './ultipa-parse.js';

const TIMEOUT_MS = 30_000;
const IDLE_TTL_MS = 5 * 60_000;

interface CachedClient {
  client: GqldbClient;
  target: UltipaTarget;
  idleTimer: NodeJS.Timeout | null;
  refCount: number;
}

const cache = new Map<string, CachedClient>();

/**
 * Build (or reuse) an authenticated Ultipa GQL client for the given
 * connection string. Cloud DBaaS deployments rate-limit logins and react
 * poorly to rapid client teardown / recreation cycles, so we cache one
 * `GqldbClient` per connection string and only tear it down after
 * `IDLE_TTL_MS` of inactivity.
 *
 * Callers should invoke `releaseUltipaClient(connectionString)` instead
 * of `client.close()` to mark themselves done.
 */
export async function createUltipaClient(connectionString: string): Promise<{
  client: GqldbClient;
  target: UltipaTarget;
}> {
  const existing = cache.get(connectionString);
  if (existing) {
    existing.refCount++;
    if (existing.idleTimer) {
      clearTimeout(existing.idleTimer);
      existing.idleTimer = null;
    }
    return { client: existing.client, target: existing.target };
  }

  const target = parseUltipaConnection(connectionString);
  const builder = new ConfigBuilder()
    .hosts(...target.hosts)
    .timeout(TIMEOUT_MS)
    .poolSize(8);
  if (target.username !== undefined) builder.username(target.username);
  if (target.password !== undefined) builder.password(target.password);
  if (target.defaultGraph) builder.defaultGraph(target.defaultGraph);
  if (target.useSSL) builder.tls({});
  const client = new GqldbClient(builder.build());
  if (target.username !== undefined) {
    await client.login(target.username, target.password ?? '');
  }
  try {
    await client.ping();
  } catch {
    /* non-fatal */
  }
  if (target.defaultGraph) {
    try {
      await client.useGraph(target.defaultGraph);
    } catch {
      /* non-fatal */
    }
  }
  cache.set(connectionString, { client, target, idleTimer: null, refCount: 1 });
  return { client, target };
}

/**
 * Mark the caller done with the cached client. Schedules teardown after
 * `IDLE_TTL_MS` if no other caller revives it first.
 */
export function releaseUltipaClient(connectionString: string): void {
  const entry = cache.get(connectionString);
  if (!entry) return;
  entry.refCount = Math.max(0, entry.refCount - 1);
  if (entry.refCount > 0) return;
  if (entry.idleTimer) clearTimeout(entry.idleTimer);
  entry.idleTimer = setTimeout(() => {
    cache.delete(connectionString);
    entry.client.close().catch(() => {
      /* best-effort */
    });
  }, IDLE_TTL_MS);
}

/** Force-evict cached client (e.g. on connection deletion). */
export async function evictUltipaClient(connectionString: string): Promise<void> {
  const entry = cache.get(connectionString);
  if (!entry) return;
  cache.delete(connectionString);
  if (entry.idleTimer) clearTimeout(entry.idleTimer);
  await entry.client.close().catch(() => {
    /* best-effort */
  });
}
