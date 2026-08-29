/**
 * Pre-validator sanitization for LLM output. Local, deterministic fixes
 * for common hallucinations that some weaker models emit even when the
 * prompt forbids them. Each fix is conservative: it only rewrites tokens
 * the safety validator would reject anyway, and it returns the list of
 * rewrites applied so the service can log/expose them as warnings.
 *
 * Out of scope: anything semantic (column choice, join correctness).
 * Those still go through the safety validator and the retry loop.
 */
export interface SanitizeResult {
    query: string;
    fixes: string[];
}
export interface SanitizeOptions {
    rowLimit: number;
    language: 'sql' | 'cypher';
    /** Set of unqualified table names known to exist in the schema. Used to
     *  detect spurious schema prefixes (e.g. SQLite has no user schemas, yet
     *  some models emit `main.Brands` because the prompt example used a prefix). */
    knownTables?: Set<string>;
    /** Strip every `<word>.<knownTable>` prefix unconditionally. Use for SQLite. */
    stripAllSchemaPrefixes?: boolean;
}
export declare function sanitize(query: string, opts: SanitizeOptions): SanitizeResult;
//# sourceMappingURL=sanitize.d.ts.map