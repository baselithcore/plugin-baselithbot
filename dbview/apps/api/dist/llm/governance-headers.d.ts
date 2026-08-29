import type { GovernanceContext } from '../common/request-context.js';
/**
 * Parse the live LLM-governance headers the BaselithCore proxy mints per
 * request (see `plugins/dbview/llm_governance.py::governed_request_headers`).
 *
 * The proxy strips any inbound copy of these before forwarding, so their
 * presence is trusted. Returns `undefined` when none are set (unpinned or the
 * request did not come through the governing proxy) — callers then fall back
 * to the spawn-time `DBVIEW_LLM_ENFORCED_*` env.
 */
type RawHeaders = Record<string, string | string[] | undefined>;
export declare function parseGovernanceHeaders(headers: RawHeaders): GovernanceContext | undefined;
export {};
//# sourceMappingURL=governance-headers.d.ts.map