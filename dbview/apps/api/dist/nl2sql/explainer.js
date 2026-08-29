const EXPLAINER_SYSTEM_EN = [
    'You are a database query explainer. You receive a generated query and the user prompt that produced it.',
    'Output ONLY valid JSON: { "explanation": string, "joinNotes": string[] }.',
    'HARD RULES:',
    '- Write all prose in ENGLISH.',
    '- explanation: 1-2 sentences in plain English. Describe what the query returns, not how SQL syntax works. Mention key filters or sort orders if present.',
    '- joinNotes: one short bullet per JOIN/relationship explaining the cardinality and intent (e.g. "JOIN orders on customers.id = orders.customer_id (1 customer -> N orders)"). Empty array if there are no joins.',
    '- NEVER include code fences, prose, or fields beyond the two listed.',
].join('\n');
const EXPLAINER_SYSTEM_IT = [
    "Sei un explainer di query verso database. Ricevi una query generata e la richiesta dell'utente che l'ha prodotta.",
    'Restituisci SOLO JSON valido: { "explanation": string, "joinNotes": string[] }.',
    'REGOLE TASSATIVE:',
    '- Scrivi tutto il testo in ITALIANO.',
    '- explanation: 1-2 frasi in italiano semplice. Descrivi cosa restituisce la query, non come funziona la sintassi SQL. Menziona i filtri o gli ordinamenti rilevanti, se presenti.',
    '- joinNotes: una breve riga per ogni JOIN/relazione che spiega cardinalità e intento (es. "JOIN orders su customers.id = orders.customer_id (1 cliente -> N ordini)"). Array vuoto se non ci sono join.',
    '- Non includere mai blocchi di codice, prosa aggiuntiva o campi diversi dai due elencati.',
].join('\n');
function systemFor(locale) {
    return locale === 'it' ? EXPLAINER_SYSTEM_IT : EXPLAINER_SYSTEM_EN;
}
function buildExplainerUserPrompt(ctx) {
    return [
        `User question: ${ctx.userPrompt}`,
        `Dialect: ${ctx.dialect}`,
        `Generated ${ctx.language.toUpperCase()}:`,
        '```',
        ctx.query.trim(),
        '```',
        'Now produce the JSON object describing this query.',
    ].join('\n');
}
/**
 * Annotate a generated query with a natural-language explanation.
 *
 * Best-effort: any failure (provider error, malformed JSON) yields an empty
 * result rather than aborting the parent request — the SQL itself is still useful.
 */
export async function explainQuery(adapter, model, ctx) {
    try {
        const completion = await adapter.complete({
            system: systemFor(ctx.locale),
            user: buildExplainerUserPrompt(ctx),
            temperature: 0,
        }, model);
        return parseExplainerJson(completion.text);
    }
    catch {
        return { explanation: '', joinNotes: [] };
    }
}
export function parseExplainerJson(text) {
    const stripped = text
        .trim()
        .replace(/^```json\s*/i, '')
        .replace(/^```\s*/i, '')
        .replace(/```\s*$/i, '');
    const start = stripped.indexOf('{');
    const end = stripped.lastIndexOf('}');
    if (start < 0 || end < start)
        return { explanation: '', joinNotes: [] };
    try {
        const obj = JSON.parse(stripped.slice(start, end + 1));
        const explanation = typeof obj.explanation === 'string' ? obj.explanation.trim() : '';
        const joinNotes = Array.isArray(obj.joinNotes)
            ? obj.joinNotes.filter((x) => typeof x === 'string' && x.trim().length > 0)
            : [];
        return { explanation, joinNotes };
    }
    catch {
        return { explanation: '', joinNotes: [] };
    }
}
//# sourceMappingURL=explainer.js.map