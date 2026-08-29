import type { LlmAdapter, LlmCompletionInput, LlmCompletionResult, StructuredContext } from './provider.js';
/**
 * Adapter for the sqlcoder model family (raw SQL completion model).
 *
 * sqlcoder is NOT chat-tuned: it expects a single prompt ending with `[SQL]`
 * and returns raw SQL (no JSON, no narrative). We:
 *   1) call Ollama's `/api/generate` (completion endpoint)
 *   2) render a sqlcoder-style prompt from the structured context
 *   3) parse raw SQL from the response
 *   4) wrap it in synthetic LlmJson so the rest of the pipeline is uniform
 *
 * Per defog/sqlcoder model card: https://huggingface.co/defog/sqlcoder-7b-2
 */
export declare class SqlcoderAdapter implements LlmAdapter {
    private readonly baseUrl;
    readonly provider: "ollama";
    readonly name = "ollama-sqlcoder";
    constructor(baseUrl: string);
    complete(input: LlmCompletionInput, model: string): Promise<LlmCompletionResult>;
}
/**
 * Render a defog/sqlcoder-2 prompt. Mirrors the official training template:
 *   ### Task → ### Database Schema → ### Answer → ```sql cue.
 * The model continues from the opening fence with raw SQL.
 *
 * Reference: https://huggingface.co/defog/sqlcoder-7b-2
 */
export declare function renderSqlcoderPrompt(ctx: StructuredContext): string;
/**
 * Extract a single SQL statement from sqlcoder's raw output. Strips markdown
 * fences, leading prose, trailing prose, and ensures the result starts with
 * a real SQL query keyword (SELECT or WITH). Returns "" when no valid
 * statement can be located — caller treats empty as a parse failure and
 * triggers a retry with adjusted temperature.
 */
export declare function extractSql(raw: string): string;
//# sourceMappingURL=sqlcoder-adapter.d.ts.map