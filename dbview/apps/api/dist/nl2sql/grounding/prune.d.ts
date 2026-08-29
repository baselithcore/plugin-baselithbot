import type { SchemaGraph } from '@dbview/shared';
export interface PruneOptions {
    /** Skip pruning entirely when the schema has at most this many tables. */
    threshold: number;
    /** Maximum number of tables to keep AFTER 1-hop FK closure. */
    maxTables: number;
}
export interface PruneResult {
    /** Pruned schema (or the original when pruning was skipped). */
    graph: SchemaGraph;
    /** True when the returned graph is a strict subset of the input. */
    pruned: boolean;
    /** Table ids removed from the input. Empty when `pruned` is false. */
    removed: string[];
    /** Tokens extracted from the prompt that drove the scoring. */
    matchedTokens: string[];
}
/**
 * Wide schemas (Salesforce Data Cloud, large datalakes) inflate the system
 * prompt past 30KB and dilute the model's attention so much that the LLM
 * picks the wrong table or invents columns. Reduce the schema to the tables
 * actually relevant to the user's question via keyword overlap, then add the
 * 1-hop FK closure so joins remain expressible.
 *
 * The function is intentionally conservative: when no token matches anything
 * (e.g. fully abstract questions like "list everything"), it returns the input
 * unchanged. Callers must treat this as best-effort and keep the full graph
 * available as a fallback for the retry loop.
 */
export declare function pruneRelationalSchema(graph: SchemaGraph, prompt: string, opts: PruneOptions): PruneResult;
/**
 * Lowercased content tokens (≥3 chars) extracted from the prompt with common
 * English + Italian stopwords removed. Quoted literals and numbers are kept
 * as raw tokens so a question like `WHERE name = "Acme"` still scores tables
 * with an `acme` column or description.
 */
export declare function tokenize(prompt: string): string[];
//# sourceMappingURL=prune.d.ts.map