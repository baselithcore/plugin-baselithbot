import { type Nl2QueryAskRequest, type Nl2QueryAskResponse } from '@dbview/shared';
import { Nl2SqlService } from './nl2sql.service.js';
import { QueryService } from '../query/query.service.js';
import { ConnectionsService } from '../connections/connections.service.js';
import { HistoryService } from '../history/history.service.js';
import { SchemaService } from '../schema/schema.service.js';
import { LlmGovernanceService } from '../llm/governance.service.js';
import type { AuthPrincipal } from '../auth/auth.types.js';
/**
 * One-shot orchestrator: NL prompt → safe query → execution → NL summary.
 *
 * Translation failures bubble (no useful query to surface). Execution and
 * summarization failures are captured into the response so the UI can show
 * the generated query plus a structured error instead of losing context.
 */
export declare class Nl2QueryAskService {
    private readonly nl2sql;
    private readonly query;
    private readonly connections;
    private readonly history;
    private readonly schemaService;
    private readonly governance;
    private readonly logger;
    constructor(nl2sql: Nl2SqlService, query: QueryService, connections: ConnectionsService, history: HistoryService, schemaService: SchemaService, governance: LlmGovernanceService);
    ask(req: Nl2QueryAskRequest, principal: AuthPrincipal): Promise<Nl2QueryAskResponse>;
}
/**
 * Decide whether an execution error is worth a corrective LLM round-trip.
 *
 * Repair the failure when the engine error reads like a fixable query bug
 * (column/table/function/syntax/type problem). Skip repair on transient
 * conditions (timeout, network, auth) — those can't be fixed by rewriting
 * the SQL and just waste an LLM call.
 */
export declare function isFixableSqlError(err: {
    code: string;
    message: string;
}): boolean;
export declare function buildRepairPrompt(originalPrompt: string, failedQuery: string, errorMsg: string): string;
//# sourceMappingURL=ask.service.d.ts.map