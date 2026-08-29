/**
 * Find the closest matches for a needle within a candidate set.
 * Uses normalized Levenshtein distance + case-insensitive comparison.
 * Returns up to `top` suggestions ordered best-first.
 *
 * Used by the NL2Query retry loop to give the model concrete hints when
 * it hallucinates table or column names.
 */
export function closestMatches(needle, candidates, top = 3) {
    if (!needle || candidates.length === 0)
        return [];
    const n = needle.toLowerCase();
    const scored = candidates.map((c) => {
        const d = distance(n, c.toLowerCase());
        const ratio = d / Math.max(n.length, c.length);
        return { name: c, d, ratio };
    });
    scored.sort((a, b) => a.d - b.d);
    // Keep only matches with at most ~40% character difference. Filters out
    // unrelated names while still suggesting typos and minor case/format variants.
    return scored
        .filter((s) => s.ratio <= 0.4)
        .slice(0, top)
        .map((s) => s.name);
}
/**
 * Map every unknown entity to its closest known matches.
 * Empty arrays are filtered out.
 */
export function buildSuggestionMap(unknown, known) {
    const out = {};
    for (const u of unknown) {
        const m = closestMatches(u, known);
        if (m.length > 0)
            out[u] = m;
    }
    return out;
}
function distance(a, b) {
    if (a === b)
        return 0;
    const al = a.length;
    const bl = b.length;
    if (al === 0)
        return bl;
    if (bl === 0)
        return al;
    let prev = new Array(bl + 1).fill(0);
    let curr = new Array(bl + 1).fill(0);
    for (let j = 0; j <= bl; j++)
        prev[j] = j;
    for (let i = 1; i <= al; i++) {
        curr[0] = i;
        for (let j = 1; j <= bl; j++) {
            const cost = a.charCodeAt(i - 1) === b.charCodeAt(j - 1) ? 0 : 1;
            const left = curr[j - 1];
            const up = prev[j];
            const diag = prev[j - 1];
            curr[j] = Math.min(left + 1, up + 1, diag + cost);
        }
        const tmp = prev;
        prev = curr;
        curr = tmp;
    }
    return prev[bl];
}
//# sourceMappingURL=suggest.js.map