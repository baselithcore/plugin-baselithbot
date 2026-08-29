import type { ExecuteQueryResponse, QueryLanguage, ResponseLocale, UnifiedSchema } from '@dbview/shared';
import type { LlmAdapter } from './llm/provider.js';
export interface SummarizerInput {
    userPrompt: string;
    query: string;
    language: QueryLanguage;
    result: ExecuteQueryResponse;
    locale?: ResponseLocale;
    /** Optional. When present, follow-up suggestions are constrained to its identifiers. */
    schema?: UnifiedSchema;
}
export interface SummarizerResult {
    summary: string;
    highlights: string[];
    followUps: string[];
}
/**
 * Generate a natural-language headline summary of a query result.
 *
 * Best-effort: any provider/parse failure yields a deterministic fallback
 * built from row count + duration so the UI always has something to show.
 */
export declare function summarizeResult(adapter: LlmAdapter, model: string, input: SummarizerInput): Promise<SummarizerResult>;
/**
 * Compact schema digest: names only (tables → columns, labels → properties,
 * collections → payload fields). Strips types/samples to keep the prompt tight
 * — the model only needs the vocabulary, not the data model semantics, since
 * it is generating natural-language follow-ups, not queries.
 */
export declare function renderSchemaDigest(schema: UnifiedSchema): string;
interface SchemaVocabulary {
    /** Lowercased identifiers known to the schema. */
    identifiers: Set<string>;
    /** Words considered ambient and not subject to grounding (locale-neutral). */
    noiseWords: Set<string>;
}
/**
 * Reject a follow-up that names a domain concept (a content word ≥4 chars) not
 * present in the schema vocabulary. Short fillers, numbers, quoted literals and
 * known noise words are ignored. The check is intentionally lenient: it only
 * blocks the obvious hallucinations (e.g. asking about `manufactured_date` when
 * the schema has no such column) while letting through natural language about
 * existing identifiers.
 */
export declare function isGroundedInSchema(question: string, vocab: SchemaVocabulary): boolean;
/**
 * Identify columns whose value is NULL/undefined in every preview row. Used
 * to alert the summarizer when a "top N by metric" query returned rows whose
 * metric is entirely NULL — otherwise the model says "no data" while the UI
 * shows a populated table, which reads as a contradiction.
 */
export declare function detectAllNullColumns(result: ExecuteQueryResponse): string[];
export declare function parseSummaryJson(text: string): SummarizerResult | null;
/**
 * Drop follow-up questions that lean on prior-turn context. Each follow-up is
 * dispatched as a fresh prompt to a stateless LLM, so anaphoric references
 * ("these sales", "the table above") become unanswerable. Anything with bare
 * demonstratives without a concrete noun anchor is rejected. The summarizer
 * prompt also instructs against this, but small/local models often slip — this
 * is the safety net.
 */
export declare function sanitizeFollowUps(items: string[]): string[];
export {};
//# sourceMappingURL=summarizer.d.ts.map