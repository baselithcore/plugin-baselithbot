/**
 * Find the closest matches for a needle within a candidate set.
 * Uses normalized Levenshtein distance + case-insensitive comparison.
 * Returns up to `top` suggestions ordered best-first.
 *
 * Used by the NL2Query retry loop to give the model concrete hints when
 * it hallucinates table or column names.
 */
export declare function closestMatches(needle: string, candidates: string[], top?: number): string[];
/**
 * Map every unknown entity to its closest known matches.
 * Empty arrays are filtered out.
 */
export declare function buildSuggestionMap(unknown: string[], known: string[]): Record<string, string[]>;
//# sourceMappingURL=suggest.d.ts.map