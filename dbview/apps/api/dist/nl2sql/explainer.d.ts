import type { Dialect, ResponseLocale, UnifiedSchema } from '@dbview/shared';
import type { LlmAdapter } from './llm/provider.js';
export interface ExplainerResult {
    explanation: string;
    joinNotes: string[];
}
export interface ExplainerInput {
    query: string;
    language: 'sql' | 'cypher';
    dialect: Dialect;
    userPrompt: string;
    schema: UnifiedSchema;
    locale?: ResponseLocale;
}
/**
 * Annotate a generated query with a natural-language explanation.
 *
 * Best-effort: any failure (provider error, malformed JSON) yields an empty
 * result rather than aborting the parent request — the SQL itself is still useful.
 */
export declare function explainQuery(adapter: LlmAdapter, model: string, ctx: ExplainerInput): Promise<ExplainerResult>;
export declare function parseExplainerJson(text: string): ExplainerResult;
//# sourceMappingURL=explainer.d.ts.map