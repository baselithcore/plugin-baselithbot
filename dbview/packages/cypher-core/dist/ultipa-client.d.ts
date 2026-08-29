import { GqldbClient } from '@ultipa-graph/ultipa-driver';
import { type UltipaTarget } from './ultipa-parse.js';
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
export declare function createUltipaClient(connectionString: string): Promise<{
    client: GqldbClient;
    target: UltipaTarget;
}>;
/**
 * Mark the caller done with the cached client. Schedules teardown after
 * `IDLE_TTL_MS` if no other caller revives it first.
 */
export declare function releaseUltipaClient(connectionString: string): void;
/** Force-evict cached client (e.g. on connection deletion). */
export declare function evictUltipaClient(connectionString: string): Promise<void>;
//# sourceMappingURL=ultipa-client.d.ts.map