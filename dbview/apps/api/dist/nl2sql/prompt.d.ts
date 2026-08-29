import type { Dialect, Nl2ConversationTurn, SchemaGraph, PropertyGraphSchema, UnifiedSchema, VectorStoreSchema } from '@dbview/shared';
export declare function compactRelationalSchema(graph: SchemaGraph): string;
export declare function compactGraphSchema(graph: PropertyGraphSchema): string;
export declare function compactVectorSchema(graph: VectorStoreSchema): string;
export interface BuildPromptArgs {
    graph: UnifiedSchema;
    dialect: Dialect;
    userPrompt: string;
    rowLimit: number;
    allowDml: boolean;
    retryFeedback?: string;
}
export declare function buildSystemPrompt(graph: UnifiedSchema, dialect: Dialect, allowDml: boolean): string;
/**
 * Pre-built, retry-invariant portion of the user prompt.
 *
 * Schema serialization + allowed-entity enumeration is O(tables × columns) and
 * for 200+ tables the resulting text exceeds 50KB. The retry loop reuses this
 * exact text — only `retryFeedback` differs between attempts — so we build it
 * once with `buildUserPromptBase` and append feedback per attempt.
 */
export interface UserPromptBase {
    readonly text: string;
}
export declare function buildUserPromptBase(args: Omit<BuildPromptArgs, 'retryFeedback'>): UserPromptBase;
export declare function withRetryFeedback(base: UserPromptBase, retryFeedback: string | undefined): string;
/**
 * Render prior conversation turns as a compact markdown block prepended to the
 * user prompt. Empty/missing history → empty string, so the cached schema text
 * + base prompt are returned unchanged (no regression on first-turn requests).
 *
 * Only the user prompt and the generated query are echoed back. Result rows
 * are deliberately omitted: they would dominate the token budget and risk
 * leaking dataset content into the model context window. Row count + ok flag
 * give the model just enough signal to know whether the prior turn succeeded.
 */
export declare function renderHistoryBlock(history: readonly Nl2ConversationTurn[] | undefined): string;
export declare function buildUserPrompt(args: BuildPromptArgs): string;
export declare function compactDocumentSchema(graph: Extract<UnifiedSchema, {
    kind: 'document';
}>): string;
export declare function compactSearchSchema(graph: Extract<UnifiedSchema, {
    kind: 'search';
}>): string;
export declare function compactKeyValueSchema(graph: Extract<UnifiedSchema, {
    kind: 'keyvalue';
}>): string;
//# sourceMappingURL=prompt.d.ts.map