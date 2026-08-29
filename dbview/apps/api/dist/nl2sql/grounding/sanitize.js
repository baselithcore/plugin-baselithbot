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
// Match the token after the keyword up to the next whitespace, `;`, `)`, or end of input.
// We classify the token afterwards: numeric literal → keep; anything else → placeholder.
const SQL_LIMIT_PLACEHOLDER = /\bLIMIT\s+([^\s;)]+)/gi;
const SQL_OFFSET_PLACEHOLDER = /\bOFFSET\s+([^\s;)]+)/gi;
const SQL_FETCH_NEXT_PLACEHOLDER = /\bFETCH\s+NEXT\s+([^\s;)]+)\s+ROWS\s+ONLY\b/gi;
const SQL_TOP_PLACEHOLDER = /\bTOP\s+([^\s;)]+)/gi;
const CYPHER_LIMIT_PLACEHOLDER = /\bLIMIT\s+([^\s;)]+)/gi;
const CYPHER_SKIP_PLACEHOLDER = /\bSKIP\s+([^\s;)]+)/gi;
const TRAILING_ELLIPSIS = /\s*(?:\.\.\.|…)\s*(?:;|$)/g;
// Trailing isolated single-letter ALL-CAPS identifier (e.g. "LIMIT 5 N" or
// "ORDER BY brand_id N"). Models sometimes leak placeholder letters after a
// valid clause — strip them. We require at least one whitespace before the
// letter so we don't mangle real identifiers.
const TRAILING_STRAY_LETTER = /\s+[A-Z]\s*;?\s*$/;
export function sanitize(query, opts) {
    let out = query;
    const fixes = [];
    out = stripTrailingEllipsis(out, fixes);
    if (opts.language === 'sql') {
        out = fixPlaceholder(out, SQL_LIMIT_PLACEHOLDER, 'LIMIT', String(opts.rowLimit), fixes);
        out = fixPlaceholder(out, SQL_OFFSET_PLACEHOLDER, 'OFFSET', '0', fixes);
        out = fixFetchNext(out, opts.rowLimit, fixes);
        out = fixPlaceholder(out, SQL_TOP_PLACEHOLDER, 'TOP', String(opts.rowLimit), fixes);
        if (opts.knownTables && opts.knownTables.size > 0) {
            out = stripBogusSchemaPrefixes(out, opts.knownTables, !!opts.stripAllSchemaPrefixes, fixes);
        }
        out = enforceNotNullOnRanking(out, fixes);
    }
    else {
        out = fixPlaceholder(out, CYPHER_LIMIT_PLACEHOLDER, 'LIMIT', String(opts.rowLimit), fixes);
        out = fixPlaceholder(out, CYPHER_SKIP_PLACEHOLDER, 'SKIP', '0', fixes);
    }
    out = stripTrailingStrayLetter(out, fixes);
    out = collapseSpacedDots(out, fixes);
    out = collapseMultiDots(out, fixes);
    out = stripOrphanDots(out, fixes);
    out = stripTrailingDot(out, fixes);
    out = out.replace(/[ \t]+$/, '');
    return { query: out, fixes };
}
/**
 * Collapse runs of two or more dots (`..`, `...` inside identifiers) to a
 * single dot. Models occasionally emit `Account..Name` or `db..table.col`.
 * Trailing `...` is handled separately by `stripTrailingEllipsis`.
 */
function collapseMultiDots(sql, fixes) {
    if (!/\.{2,}/.test(sql))
        return sql;
    fixes.push('collapsed consecutive dots');
    return sql.replace(/\.{2,}/g, '.');
}
/**
 * Remove orphan dots that are not between two identifiers. Catches patterns
 * like `SELECT . FROM x`, `SELECT a, . , b FROM x`, `WHERE a = .` produced by
 * weak local models leaking placeholders. Conservative: leaves valid
 * `<ident>.<ident>` references alone.
 */
function stripOrphanDots(sql, fixes) {
    let out = sql;
    let changed = false;
    // `<ws|,|(> . <ws|,|)|;|end>` — standalone orphan dot.
    out = out.replace(/([\s,(])\.(?=[\s,);]|$)/g, (_, pre) => {
        changed = true;
        return pre;
    });
    // Leading dot on an identifier when preceded by ws/comma/paren: `, .Name`.
    out = out.replace(/(^|[\s,(])\.([A-Za-z_])/g, (_, pre, c) => {
        changed = true;
        return `${pre}${c}`;
    });
    // Trailing dot immediately before `,` or `)`: `a.,` `b.)`.
    out = out.replace(/\.(?=[,)])/g, () => {
        changed = true;
        return '';
    });
    if (changed)
        fixes.push('stripped orphan dot tokens');
    return out;
}
function collapseSpacedDots(sql, fixes) {
    // Match `<ident> . <ident>` with whitespace around the dot — collapses to `<ident>.<ident>`.
    // Required because some models emit `Brands . brand_id` which the SQL parser
    // tokenizes as three separate tokens and chokes on the bare dot.
    const re = /([A-Za-z_]\w*)\s+\.\s+([A-Za-z_]\w*)/g;
    if (!re.test(sql))
        return sql;
    re.lastIndex = 0;
    fixes.push('collapsed spaced dot in qualified identifier');
    return sql.replace(re, '$1.$2');
}
function stripTrailingDot(sql, fixes) {
    const re = /\s*\.\s*;?\s*$/;
    if (!re.test(sql))
        return sql;
    fixes.push('removed trailing standalone dot');
    return sql.replace(re, sql.includes(';') ? ';' : '');
}
function fixPlaceholder(sql, pattern, keyword, fallback, fixes) {
    return sql.replace(pattern, (match, token) => {
        if (/^\d+$/.test(token))
            return match;
        fixes.push(`${keyword} ${token} → ${keyword} ${fallback}`);
        return `${keyword} ${fallback}`;
    });
}
function fixFetchNext(sql, rowLimit, fixes) {
    return sql.replace(SQL_FETCH_NEXT_PLACEHOLDER, (match, token) => {
        if (/^\d+$/.test(token))
            return match;
        fixes.push(`FETCH NEXT ${token} ROWS ONLY → FETCH NEXT ${rowLimit} ROWS ONLY`);
        return `FETCH NEXT ${rowLimit} ROWS ONLY`;
    });
}
function stripTrailingEllipsis(sql, fixes) {
    if (!TRAILING_ELLIPSIS.test(sql))
        return sql;
    TRAILING_ELLIPSIS.lastIndex = 0;
    fixes.push('removed trailing ellipsis');
    return sql.replace(TRAILING_ELLIPSIS, (m) => (m.trimEnd().endsWith(';') ? ';' : ''));
}
function stripBogusSchemaPrefixes(sql, knownTables, stripAll, fixes) {
    // Match `prefix.table` where `prefix` is a bare identifier and `table` matches
    // a known unqualified table name. Skip cases where `prefix.table` itself is in
    // knownTables (i.e. the schema prefix is real).
    const pattern = /\b([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)\b/g;
    return sql.replace(pattern, (match, prefix, table) => {
        const qualified = `${prefix}.${table}`;
        if (knownTables.has(qualified))
            return match;
        const lowerTables = new Set([...knownTables].map((t) => t.toLowerCase()));
        if (!lowerTables.has(table.toLowerCase()))
            return match;
        if (!stripAll && knownTables.has(prefix))
            return match;
        fixes.push(`stripped bogus prefix "${prefix}." from "${qualified}"`);
        return table;
    });
}
/**
 * "Top N by X" ranking queries on a nullable metric column return NULL-valued
 * rows first on engines whose `ORDER BY ... DESC` defaults to NULLS FIRST
 * (Trino/Salesforce Data Cloud, Oracle). The summarizer then truthfully
 * reports "all values are null" while the table shows real-looking rows,
 * which reads as a contradiction. Inject `WHERE <col> IS NOT NULL` whenever
 * the LLM forgot it. Conservative scope:
 *   - only top-level statements (no CTE / subquery) to avoid mis-targeting
 *   - only when ORDER BY references a single bare column (no expression)
 *   - skipped when LIMIT/TOP/FETCH is absent (not a top-N pattern)
 *   - skipped when the column already appears in an `IS NOT NULL` predicate
 */
function enforceNotNullOnRanking(sql, fixes) {
    if (/\(\s*SELECT\b/i.test(sql))
        return sql;
    if (/\bWITH\b/i.test(sql))
        return sql;
    const hasLimit = /\bLIMIT\s+\d+/i.test(sql) ||
        /\bFETCH\s+(?:FIRST|NEXT)\s+\d+/i.test(sql) ||
        /\bSELECT\s+TOP\s+\d+/i.test(sql);
    if (!hasLimit)
        return sql;
    // Anchor the identifier on a word boundary then reject `(` to catch function
    // calls (`COUNT(*)`, `SUM(x)`, ...) without letting the regex engine backtrack
    // into a shorter prefix. Aggregates never return NULL and don't need the guard.
    const orderByMatch = /\bORDER\s+BY\s+([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)\b(?!\()(?:\s+(ASC|DESC))?/i.exec(sql);
    if (!orderByMatch)
        return sql;
    const col = orderByMatch[1];
    if (!col)
        return sql;
    const bare = col.includes('.') ? col.split('.').pop() : col;
    const isNotNullRe = new RegExp(`\\b${escapeRe(bare)}\\s+IS\\s+NOT\\s+NULL\\b`, 'i');
    if (isNotNullRe.test(sql))
        return sql;
    const whereRe = /\bWHERE\b/i;
    let out;
    if (whereRe.test(sql)) {
        out = sql.replace(/(\bWHERE\b\s+[\s\S]*?)(\s+(?:GROUP\s+BY|HAVING|ORDER\s+BY|LIMIT|FETCH\s+(?:FIRST|NEXT))\b)/i, (_, head, tail) => `${head} AND ${col} IS NOT NULL${tail}`);
    }
    else {
        out = sql.replace(/(\s+)(GROUP\s+BY|HAVING|ORDER\s+BY)\b/i, (_, ws, kw) => `${ws}WHERE ${col} IS NOT NULL ${kw}`);
    }
    if (out === sql)
        return sql;
    fixes.push(`added ${col} IS NOT NULL to exclude nulls from top-N ranking`);
    return out;
}
function escapeRe(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
function stripTrailingStrayLetter(sql, fixes) {
    const match = sql.match(TRAILING_STRAY_LETTER);
    if (!match)
        return sql;
    fixes.push(`removed trailing stray token "${match[0].trim()}"`);
    const semi = match[0].includes(';') ? ';' : '';
    return sql.replace(TRAILING_STRAY_LETTER, semi);
}
//# sourceMappingURL=sanitize.js.map