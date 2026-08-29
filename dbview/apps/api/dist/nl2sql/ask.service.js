var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
import { Injectable, Logger } from '@nestjs/common';
import { DbviewError, isIncompatibleOllamaModel, isSqlcoderModel, } from '@dbview/shared';
import { Nl2SqlService } from './nl2sql.service.js';
import { QueryService } from '../query/query.service.js';
import { ConnectionsService } from '../connections/connections.service.js';
import { HistoryService } from '../history/history.service.js';
import { SchemaService } from '../schema/schema.service.js';
import { LlmGovernanceService } from '../llm/governance.service.js';
import { createChatAdapter, defaultExplainModel } from './llm/factory.js';
import { summarizeResult } from './summarizer.js';
import { instrumentLlmAdapter } from '../observability/instrument-llm.js';
/**
 * One-shot orchestrator: NL prompt → safe query → execution → NL summary.
 *
 * Translation failures bubble (no useful query to surface). Execution and
 * summarization failures are captured into the response so the UI can show
 * the generated query plus a structured error instead of losing context.
 */
let Nl2QueryAskService = class Nl2QueryAskService {
    nl2sql;
    query;
    connections;
    history;
    schemaService;
    governance;
    logger = new Logger('Nl2QueryAskService');
    constructor(nl2sql, query, connections, history, schemaService, governance) {
        this.nl2sql = nl2sql;
        this.query = query;
        this.connections = connections;
        this.history = history;
        this.schemaService = schemaService;
        this.governance = governance;
    }
    async ask(req, principal) {
        const t0 = Date.now();
        let translation = await this.nl2sql.translate({
            connectionId: req.connectionId,
            prompt: req.prompt,
            provider: req.provider,
            model: req.model,
            allowDml: false,
            rowLimit: req.rowLimit,
            locale: req.locale,
            history: req.history,
        }, principal);
        let result = null;
        let executionError = null;
        try {
            result = await this.query.execute({
                connectionId: req.connectionId,
                query: translation.query,
                rowLimit: req.rowLimit,
            }, principal);
        }
        catch (err) {
            executionError = toAskError(err);
            this.logger.warn(`ask execute-failed code=${executionError.code} msg=${executionError.message}`);
        }
        // Execution-error repair pass. The validator only catches schema/safety
        // problems; the engine catches everything else (column-doesn't-exist,
        // type mismatch, ambiguous reference, function not found). When the
        // failure looks like a fixable SQL bug — not a transient or permission
        // problem — we feed the original query + engine error back to the LLM
        // for one corrective attempt. Capped to a single repair to avoid
        // unbounded loops on a model that keeps producing the same broken query.
        if (result === null && executionError && isFixableSqlError(executionError)) {
            const repairPrompt = buildRepairPrompt(req.prompt, translation.query, executionError.message);
            this.logger.log(`ask repair-attempt code=${executionError.code} reason=${truncate(executionError.message, 120)}`);
            try {
                const repaired = await this.nl2sql.translate({
                    connectionId: req.connectionId,
                    prompt: repairPrompt,
                    provider: req.provider,
                    model: req.model,
                    allowDml: false,
                    rowLimit: req.rowLimit,
                    locale: req.locale,
                    // Skip conversation history on repair: the repair prompt already
                    // embeds the failed query verbatim. Re-replaying the prior turns
                    // would dilute the model's focus on the specific engine error.
                    history: [],
                }, principal);
                try {
                    const repairedResult = await this.query.execute({
                        connectionId: req.connectionId,
                        query: repaired.query,
                        rowLimit: req.rowLimit,
                    }, principal);
                    translation = repaired;
                    result = repairedResult;
                    executionError = null;
                    this.logger.log(`ask repair-success rows=${result.rowCount}`);
                }
                catch (err) {
                    // Repair query also failed at execution; surface the new error so
                    // the user sees the most recent attempt.
                    translation = repaired;
                    executionError = toAskError(err);
                    this.logger.warn(`ask repair-failed code=${executionError.code} msg=${truncate(executionError.message, 120)}`);
                }
            }
            catch (err) {
                this.logger.warn(`ask repair-translate-failed: ${err.message}`);
            }
        }
        let summary = '';
        let highlights = [];
        let followUps = [];
        if (result) {
            try {
                // Explain/summarize scope: an enforced central pin overrides the
                // request's provider/model and per-user BYOK; otherwise keep the
                // caller's summary-model preference.
                const explainGov = this.governance.resolveExplain(req.provider, principal);
                const adapter = instrumentLlmAdapter(createChatAdapter(explainGov.provider, explainGov.auth), 'ask');
                const model = this.governance.state().explain.enforced
                    ? explainGov.model
                    : pickSummaryModel(req.provider, req.model, translation.model);
                // Ground follow-ups in the actual schema so the model cannot invent
                // columns/tables. Use the cached graph; do not force a refresh.
                const schema = await this.schemaService
                    .getGraph(req.connectionId, principal)
                    .catch(() => undefined);
                this.logger.log(`ask summarize provider=${req.provider} model=${model} schema=${schema ? 'on' : 'off'}`);
                const summarized = await summarizeResult(adapter, model, {
                    userPrompt: req.prompt,
                    query: translation.query,
                    language: translation.language,
                    result,
                    locale: req.locale,
                    schema,
                });
                summary = summarized.summary;
                highlights = summarized.highlights;
                followUps = summarized.followUps;
            }
            catch (err) {
                this.logger.warn(`ask summarize-failed: ${err.message}`);
            }
        }
        const totalDurationMs = Date.now() - t0;
        this.logger.log(`ask ok provider=${req.provider} model=${translation.model} rows=${result?.rowCount ?? 'n/a'} highlights=${highlights.length} followUps=${followUps.length} totalMs=${totalDurationMs}`);
        // Persist the turn for history/favorites. Non-blocking: record() swallows
        // disk errors and returns null so a flaky filesystem can't break the user
        // response that's already computed.
        let connectionName = req.connectionId;
        try {
            connectionName = this.connections.get(req.connectionId, principal).name;
        }
        catch {
            // Connection might have been deleted mid-flight; persist with id as name.
        }
        this.history.record({
            connectionId: req.connectionId,
            connectionName,
            prompt: req.prompt,
            query: translation.query,
            language: translation.language,
            provider: req.provider,
            model: translation.model,
            summary: summary || null,
            rowCount: result?.rowCount ?? null,
            durationMs: result?.durationMs ?? null,
            ok: !executionError,
            errorCode: executionError?.code ?? null,
            errorMessage: executionError?.message ?? null,
        }, principal.id);
        return {
            translation,
            result,
            executionError,
            summary,
            highlights,
            followUps,
            totalDurationMs,
        };
    }
};
Nl2QueryAskService = __decorate([
    Injectable(),
    __metadata("design:paramtypes", [Nl2SqlService,
        QueryService,
        ConnectionsService,
        HistoryService,
        SchemaService,
        LlmGovernanceService])
], Nl2QueryAskService);
export { Nl2QueryAskService };
/**
 * Pick a chat-capable model for summarization.
 *
 * Order: user-chosen model (if chat-capable) > query-generation model (if chat-capable) >
 * provider default explain model. Sqlcoder (raw completion) and embedding models are
 * unfit for JSON summarization and fall through.
 */
function pickSummaryModel(provider, userModel, translationModel) {
    const isChatCapable = (name) => {
        if (!name)
            return false;
        if (provider === 'ollama')
            return !isSqlcoderModel(name) && !isIncompatibleOllamaModel(name);
        return true;
    };
    if (isChatCapable(userModel))
        return userModel;
    if (isChatCapable(translationModel))
        return translationModel;
    return defaultExplainModel(provider);
}
/**
 * Decide whether an execution error is worth a corrective LLM round-trip.
 *
 * Repair the failure when the engine error reads like a fixable query bug
 * (column/table/function/syntax/type problem). Skip repair on transient
 * conditions (timeout, network, auth) — those can't be fixed by rewriting
 * the SQL and just waste an LLM call.
 */
export function isFixableSqlError(err) {
    const blob = `${err.code} ${err.message}`.toLowerCase();
    // Skip — same query would fail the same way.
    const skipPatterns = [
        'timeout',
        'timed out',
        'connection',
        'econnref',
        'enotfound',
        'auth',
        'unauthor',
        'forbidd',
        'permission',
        'rate limit',
        'too many request',
        'not reachable',
    ];
    for (const p of skipPatterns)
        if (blob.includes(p))
            return false;
    // Retry — engine returned a deterministic SQL-shape complaint.
    const retryPatterns = [
        'column',
        'table',
        'relation',
        'syntax',
        'unknown',
        'does not exist',
        'no such',
        'ambiguous',
        'invalid',
        'mismatch',
        'cannot cast',
        'cast(',
        'function',
        'identifier',
        'object not found',
        'datasource',
        'unrecognized',
        'unexpected',
    ];
    for (const p of retryPatterns)
        if (blob.includes(p))
            return true;
    return false;
}
export function buildRepairPrompt(originalPrompt, failedQuery, errorMsg) {
    return [
        originalPrompt,
        '',
        'PRIOR ATTEMPT FAILED AT EXECUTION — DO NOT REPEAT THE SAME QUERY:',
        `Failed query: ${failedQuery}`,
        `Engine error: ${errorMsg}`,
        '',
        'Produce a corrected query that addresses the engine error above. Stay strictly within the schema. If the error names a missing column/table, do not invent a replacement — pick a real column/table from the schema or omit the predicate and explain the limitation.',
    ].join('\n');
}
function truncate(s, max) {
    return s.length > max ? `${s.slice(0, max)}…` : s;
}
function toAskError(err) {
    if (err instanceof DbviewError) {
        return { code: err.code, message: err.message };
    }
    if (err instanceof Error) {
        return { code: 'execution_failed', message: err.message };
    }
    return { code: 'execution_failed', message: String(err) };
}
//# sourceMappingURL=ask.service.js.map