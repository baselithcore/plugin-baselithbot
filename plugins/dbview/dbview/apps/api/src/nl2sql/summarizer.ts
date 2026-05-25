import type {
  ExecuteQueryResponse,
  QueryLanguage,
  ResponseLocale,
  UnifiedSchema,
} from '@dbview/shared';
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

const MAX_PREVIEW_ROWS = 12;
const MAX_CELL_CHARS = 80;
const MAX_HIGHLIGHTS = 4;
const MAX_FOLLOW_UPS = 3;

const SUMMARIZER_SYSTEM_EN = [
  'You are a friendly senior data analyst replying inside a chat assistant. You receive the user question,',
  'the query that produced the answer, and a sample of the result rows. Write the answer as a natural',
  'conversational reply: the user should be able to read just your prose and feel they got an answer,',
  'without needing to look at the table below.',
  'HARD RULES:',
  '- Output ONLY valid JSON: { "summary": string, "highlights": string[], "followUps": string[] }.',
  '- Write everything in ENGLISH.',
  '- summary: 2 to 4 sentences. Address the user directly ("you", "your data"). Open with the headline',
  '  answer, then weave specific numbers, names and patterns from the rows INTO the sentences ("The top',
  '  three customers are Acme ($1.2M), TopCo ($980k) and Globex ($740k), together about 62% of revenue").',
  '  Do NOT write phrases like "the query returned N rows", "see the table", "the result shows", "based on',
  '  the data". Talk about the data, not about the query. If the result is empty, say so naturally and',
  '  suggest a likely cause in plain language.',
  '- highlights: 0-3 short strings (max ~70 chars each) ONLY when they add information not already in the',
  '  summary — e.g. a notable outlier, a secondary stat, a caveat. Each highlight reads as a small natural',
  '  fact ("Acme alone is 28% of total revenue", not "Acme — $1.2M"). Empty array is the right answer when',
  '  the summary already covers everything; do not pad.',
  '- followUps: 0-3 follow-up questions the user might naturally ask next, grounded in the rows you saw.',
  '  CRITICAL — every follow-up MUST be SELF-CONTAINED: it will be sent verbatim as a brand-new prompt to',
  '  another LLM that has NO memory of this conversation, this query, or these rows. Therefore:',
  '    * NEVER use anaphora: no "these", "those", "this", "that", "such", "the above", "the previous",',
  '      "them", "the ones shown", "the result", "the table". Each follow-up reads on its own.',
  '    * Inline the concrete entities by name and any relevant scope (time window, filter, ordering) from',
  '      the original question. Example — bad: "What are the details of these sales?"; good: "Show the',
  '      individual sale records for The Brunette, Orange, Hat, F12 Berlinetta and Extra, including date,',
  '      customer and price".',
  '    * Diversify intent across the three slots — pick from: drill-down on a specific row, breakdown by a',
  '      related dimension (time, geography, category), comparison (top vs bottom, this vs other group),',
  '      trend over time, ratio or share, related entity (customers, suppliers, etc.). Do not produce three',
  '      variations of the same question.',
  '    * Each question stays short (max ~110 chars) and answerable with one SQL/Cypher query against the',
  '      same database. Avoid open-ended "why" questions a query cannot answer.',
  '    * GROUNDING: only reference tables, columns, labels, relationships, properties, collections or',
  '      payload fields that appear in the AVAILABLE SCHEMA block of the user message (if present). NEVER',
  '      invent a column or concept (e.g. do not ask about a date/time/region/category if no such',
  '      identifier exists in the schema). If you cannot ground a follow-up in the schema, drop it.',
  '    * Use empty array when nothing meaningful can be asked next (e.g. trivial single-value result, or',
  '      no further sensible question can be grounded in the schema).',
  '- Never describe SQL syntax, column indices, the query structure, or your own reasoning. Just talk about',
  '  the data as a human analyst would.',
  '- No code fences, no preamble, no fields beyond the three listed.',
].join('\n');

const SUMMARIZER_SYSTEM_IT = [
  'Sei un data analyst senior e cordiale che risponde dentro un assistente chat. Ricevi la domanda',
  "dell'utente, la query che ha prodotto la risposta e un campione di righe del risultato. Scrivi la",
  "risposta come una replica conversazionale naturale: l'utente deve poter leggere solo la tua prosa e",
  'sentire di aver ricevuto una risposta, senza dover guardare la tabella sotto.',
  'REGOLE TASSATIVE:',
  '- Restituisci SOLO JSON valido: { "summary": string, "highlights": string[], "followUps": string[] }.',
  '- Scrivi tutto in ITALIANO, in tono naturale e diretto (dai del tu).',
  "- summary: 2-4 frasi. Rivolgiti direttamente all'utente. Apri con la risposta principale, poi intreccia",
  '  numeri, nomi e pattern concreti delle righe DENTRO le frasi ("I tre clienti più importanti sono Acme',
  '  con €1,2M, TopCo con €980k e Globex con €740k, insieme circa il 62% del fatturato"). NON usare frasi',
  '  come "la query ha restituito N righe", "vedi la tabella", "il risultato mostra", "in base ai dati".',
  '  Parla dei dati, non della query. Se il risultato è vuoto, dillo in modo naturale e suggerisci una',
  '  causa probabile in linguaggio semplice.',
  '- highlights: 0-3 brevi stringhe (max ~70 caratteri ciascuna) SOLO se aggiungono informazioni non già',
  '  presenti nel summary — es. un outlier rilevante, una stat secondaria, un caveat. Ogni highlight è un',
  '  piccolo fatto naturale ("Acme da solo vale il 28% del fatturato totale", non "Acme — €1,2M"). Array',
  '  vuoto è la risposta giusta se il summary copre già tutto; non riempire per riempire.',
  "- followUps: 0-3 domande di approfondimento che l'utente potrebbe porre dopo, basate sulle righe viste.",
  '  CRITICO — ogni followUp DEVE essere AUTOSUFFICIENTE: verrà inviato pari pari come nuovo prompt a un',
  '  altro LLM che NON ha memoria di questa conversazione, di questa query o di queste righe. Quindi:',
  '    * NIENTE anafora: vietate parole come "questi", "queste", "tali", "questo", "quello", "i suddetti",',
  '      "i precedenti", "il risultato", "la tabella", "quelli mostrati". Ogni domanda si legge da sola.',
  '    * Cita esplicitamente le entità per nome e lo scope rilevante (finestra temporale, filtro, ordine)',
  '      della domanda originale. Esempio — male: "Quali sono i dettagli di queste vendite?"; bene:',
  '      "Mostra le singole vendite di The Brunette, Orange, Hat, F12 Berlinetta ed Extra, con data,',
  '      cliente e prezzo".',
  '    * Diversifica gli intenti fra i tre slot — scegli da: drill-down su una riga specifica, breakdown',
  '      per una dimensione correlata (tempo, area geografica, categoria), confronto (top vs bottom,',
  '      questo gruppo vs altro gruppo), trend nel tempo, rapporto o percentuale, entità collegata',
  '      (clienti, fornitori, ecc.). Non produrre tre varianti della stessa domanda.',
  '    * Ogni domanda resta breve (max ~110 caratteri) e risolvibile con una query SQL/Cypher sullo',
  '      stesso database. Evita "perché" aperti a cui una query non può rispondere.',
  '    * GROUNDING: cita SOLO tabelle, colonne, etichette, relazioni, proprietà, collection e campi',
  '      payload presenti nel blocco AVAILABLE SCHEMA del messaggio utente (se presente). NON inventare',
  '      una colonna o un concetto (es. non chiedere di date/tempo/regione/categoria se nessun',
  '      identificatore corrispondente esiste nello schema). Se non puoi ancorare una domanda allo',
  '      schema, scartala.',
  "    * Array vuoto quando non c'è nulla di sensato da chiedere dopo (es. risultato banale a valore",
  '      singolo, o nessuna ulteriore domanda sensata può essere ancorata allo schema).',
  '- Non descrivere sintassi SQL, indici di colonne, struttura della query o il tuo ragionamento. Parla',
  '  solo dei dati, come farebbe un analista in carne e ossa.',
  '- Niente blocchi di codice, niente preamboli, nessun campo oltre ai tre elencati.',
].join('\n');

function systemFor(locale: ResponseLocale | undefined): string {
  return locale === 'it' ? SUMMARIZER_SYSTEM_IT : SUMMARIZER_SYSTEM_EN;
}

interface SummaryJson {
  summary?: unknown;
  highlights?: unknown;
  followUps?: unknown;
  follow_ups?: unknown;
}

/**
 * Generate a natural-language headline summary of a query result.
 *
 * Best-effort: any provider/parse failure yields a deterministic fallback
 * built from row count + duration so the UI always has something to show.
 */
export async function summarizeResult(
  adapter: LlmAdapter,
  model: string,
  input: SummarizerInput,
): Promise<SummarizerResult> {
  const vocab = input.schema ? collectSchemaVocabulary(input.schema) : null;
  try {
    const completion = await adapter.complete(
      {
        system: systemFor(input.locale),
        user: buildUserPrompt(input),
        temperature: 0.1,
      },
      model,
    );
    const parsed = parseSummaryJson(completion.text);
    if (parsed && parsed.summary) {
      const grounded = vocab
        ? parsed.followUps.filter((q) => isGroundedInSchema(q, vocab))
        : parsed.followUps;
      return { ...parsed, followUps: grounded };
    }
  } catch {
    // fall through to deterministic fallback
  }
  return {
    summary: deterministicFallback(input.result, input.locale),
    highlights: [],
    followUps: [],
  };
}

function buildUserPrompt(input: SummarizerInput): string {
  const { result } = input;
  const preview = renderPreview(result);
  const more = result.rowCount > MAX_PREVIEW_ROWS ? ` (showing first ${MAX_PREVIEW_ROWS})` : '';
  const lines = [
    `User question: ${input.userPrompt}`,
    `Query (${input.language}): \`\`\`\n${input.query.trim()}\n\`\`\``,
    `Rows returned: ${result.rowCount}${result.truncated ? ' (truncated)' : ''}`,
    `Latency: ${result.durationMs}ms`,
    `Result preview${more}:`,
    preview,
  ];
  const allNullCols = detectAllNullColumns(result);
  if (allNullCols.length > 0) {
    lines.push(
      '',
      `IMPORTANT — column(s) [${allNullCols.join(', ')}] are NULL in every returned row. The query did not filter NULL values out, so the rows shown are not meaningful answers to the user question. State this explicitly in the summary (e.g. "the query returned ${result.rowCount} rows but the metric is NULL on all of them — likely the column is unpopulated for those records or the query should filter \`IS NOT NULL\`") instead of pretending the values exist or that the result is empty.`,
    );
  }
  if (input.schema) {
    lines.push(
      '',
      'AVAILABLE SCHEMA — every table, column, label, relationship type, property, collection and payload field that follow-up questions may reference. Inventing any identifier outside this list is a critical error. Do NOT mention timestamps, dates, geographies, categories or any concept whose backing identifier is not present here.',
      renderSchemaDigest(input.schema),
    );
  }
  lines.push('', 'Now produce the JSON object answering the user.');
  return lines.join('\n');
}

/**
 * Compact schema digest: names only (tables → columns, labels → properties,
 * collections → payload fields). Strips types/samples to keep the prompt tight
 * — the model only needs the vocabulary, not the data model semantics, since
 * it is generating natural-language follow-ups, not queries.
 */
export function renderSchemaDigest(schema: UnifiedSchema): string {
  if (schema.kind === 'relational') {
    const lines: string[] = ['Tables (table → columns):'];
    for (const t of schema.tables) {
      const cols = t.columns.map((c) => c.name).join(', ');
      lines.push(`- ${t.id}: ${cols}`);
    }
    if (schema.edges.length) {
      lines.push('Foreign keys:');
      for (const e of schema.edges) {
        lines.push(`- ${e.source}.${e.sourceColumn} -> ${e.target}.${e.targetColumn}`);
      }
    }
    return lines.join('\n');
  }
  if (schema.kind === 'graph') {
    const lines: string[] = ['Node labels (label → properties):'];
    for (const l of schema.labels) {
      const props = l.properties.map((p) => p.name).join(', ');
      lines.push(`- :${l.label}: ${props || '(no properties)'}`);
    }
    if (schema.relationships.length) {
      lines.push('Relationships:');
      for (const r of schema.relationships) {
        const propList = r.properties.map((p) => p.name).join(', ');
        const tail = propList ? ` { ${propList} }` : '';
        lines.push(`- (:${r.source})-[:${r.type}]->(:${r.target})${tail}`);
      }
    }
    return lines.join('\n');
  }
  if (schema.kind === 'vector') {
    const lines: string[] = ['Collections (collection → payload fields):'];
    for (const c of schema.collections) {
      const fields = c.payloadFields.map((f) => f.name).join(', ');
      lines.push(`- ${c.name}: ${fields || '(no payload fields)'}`);
    }
    return lines.join('\n');
  }
  if (schema.kind === 'keyvalue') {
    const lines: string[] = ['Namespaces (pattern → types, key count):'];
    for (const n of schema.namespaces) {
      lines.push(`- ${n.pattern}: ${n.types.join('|') || '?'} (${n.keyCount} keys)`);
    }
    return lines.join('\n');
  }
  if (schema.kind === 'search') {
    const lines: string[] = ['Indices (name → fields):'];
    for (const idx of schema.indices) {
      const fields = idx.fields
        .slice(0, 12)
        .map((f) => f.name)
        .join(', ');
      lines.push(`- ${idx.name}: ${fields || '(no fields)'}`);
    }
    return lines.join('\n');
  }
  // document
  const lines: string[] = ['Collections (name → fields):'];
  for (const c of schema.collections) {
    const fields = c.fields
      .slice(0, 12)
      .map((f) => f.name)
      .join(', ');
    lines.push(`- ${c.name}: ${fields || '(no fields)'}`);
  }
  return lines.join('\n');
}

interface SchemaVocabulary {
  /** Lowercased identifiers known to the schema. */
  identifiers: Set<string>;
  /** Words considered ambient and not subject to grounding (locale-neutral). */
  noiseWords: Set<string>;
}

const NOISE_WORDS = new Set<string>([
  // English fillers + verbs
  'show',
  'list',
  'count',
  'top',
  'bottom',
  'rank',
  'order',
  'sort',
  'group',
  'average',
  'mean',
  'median',
  'sum',
  'total',
  'min',
  'max',
  'how',
  'what',
  'which',
  'when',
  'who',
  'where',
  'with',
  'without',
  'and',
  'or',
  'the',
  'a',
  'an',
  'of',
  'for',
  'by',
  'in',
  'on',
  'per',
  'each',
  'all',
  'any',
  'last',
  'first',
  'highest',
  'lowest',
  'most',
  'least',
  'between',
  'over',
  'under',
  'compare',
  'find',
  'give',
  'me',
  'us',
  'have',
  'has',
  'are',
  'is',
  'were',
  'was',
  'do',
  'does',
  'did',
  'than',
  'to',
  'from',
  'this',
  'that',
  'these',
  'those',
  'as',
  'than',
  'records',
  'rows',
  'entries',
  'breakdown',
  'trend',
  'share',
  'ratio',
  'percentage',
  'percent',
  'data',
  'value',
  'values',
  'name',
  'names',
  // Italian fillers + verbs
  'mostra',
  'mostrami',
  'elenca',
  'conta',
  'classifica',
  'ordina',
  'raggruppa',
  'media',
  'mediana',
  'somma',
  'totale',
  'massimo',
  'minimo',
  'quanti',
  'quante',
  'quanto',
  'qual',
  'quale',
  'quali',
  'come',
  'dove',
  'quando',
  'chi',
  'cosa',
  'che',
  'con',
  'senza',
  'e',
  'o',
  'il',
  'lo',
  'la',
  'i',
  'gli',
  'le',
  'di',
  'a',
  'da',
  'in',
  'su',
  'per',
  'tra',
  'fra',
  'ogni',
  'tutti',
  'tutte',
  'nessun',
  'nessuna',
  'qualche',
  'più',
  'meno',
  'tra',
  'oltre',
  'sotto',
  'confronta',
  'trova',
  'dammi',
  'avere',
  'sono',
  'è',
  'era',
  'erano',
  'fare',
  'fai',
  'più',
  'meno',
  'numero',
  'valore',
  'valori',
  'nome',
  'nomi',
  'media',
  'rapporto',
  'percentuale',
  'dato',
  'dati',
  'ricorrenti',
  'ordinati',
  'crescente',
  'decrescente',
  'prima',
  'dopo',
]);

function collectSchemaVocabulary(schema: UnifiedSchema): SchemaVocabulary {
  const ids = new Set<string>();
  const add = (raw: string | undefined) => {
    if (!raw) return;
    for (const part of raw.toLowerCase().split(/[^a-z0-9]+/)) {
      if (part.length >= 3) ids.add(part);
    }
  };
  if (schema.kind === 'relational') {
    for (const t of schema.tables) {
      add(t.id);
      add(t.name);
      for (const c of t.columns) add(c.name);
    }
  } else if (schema.kind === 'graph') {
    for (const l of schema.labels) {
      add(l.label);
      for (const p of l.properties) add(p.name);
    }
    for (const r of schema.relationships) {
      add(r.type);
      add(r.source);
      add(r.target);
      for (const p of r.properties) add(p.name);
    }
  } else if (schema.kind === 'vector') {
    for (const c of schema.collections) {
      add(c.name);
      for (const f of c.payloadFields) add(f.name);
    }
  } else if (schema.kind === 'keyvalue') {
    for (const n of schema.namespaces) {
      add(n.pattern);
      for (const k of n.sampleKeys) add(k);
    }
  } else if (schema.kind === 'search') {
    for (const i of schema.indices) {
      add(i.name);
      for (const f of i.fields) add(f.name);
    }
  } else {
    for (const c of schema.collections) {
      add(c.name);
      for (const f of c.fields) add(f.name);
    }
  }
  return { identifiers: ids, noiseWords: NOISE_WORDS };
}

/**
 * Reject a follow-up that names a domain concept (a content word ≥4 chars) not
 * present in the schema vocabulary. Short fillers, numbers, quoted literals and
 * known noise words are ignored. The check is intentionally lenient: it only
 * blocks the obvious hallucinations (e.g. asking about `manufactured_date` when
 * the schema has no such column) while letting through natural language about
 * existing identifiers.
 */
export function isGroundedInSchema(question: string, vocab: SchemaVocabulary): boolean {
  // Strip quoted literals and numbers — they are values, not identifiers.
  const cleaned = question
    .replace(/"[^"]*"|'[^']*'/g, ' ')
    .replace(/\b\d+(?:[.,]\d+)?\b/g, ' ')
    .toLowerCase();
  const tokens = cleaned.split(/[^a-z0-9_]+/).filter(Boolean);
  for (const tok of tokens) {
    if (tok.length < 4) continue;
    if (vocab.noiseWords.has(tok)) continue;
    if (vocab.identifiers.has(tok)) continue;
    // Allow tokens whose stem matches an identifier (e.g. "customers" → "customer").
    const stem = tok.replace(/(?:s|es|ies|i|e)$/, '');
    if (stem.length >= 3 && vocab.identifiers.has(stem)) continue;
    // Allow partial containment for compound identifiers (e.g. "price" ⊂ "option_set_price").
    let matched = false;
    for (const id of vocab.identifiers) {
      if (id.includes(tok) || tok.includes(id)) {
        matched = true;
        break;
      }
    }
    if (matched) continue;
    return false;
  }
  return true;
}

/**
 * Identify columns whose value is NULL/undefined in every preview row. Used
 * to alert the summarizer when a "top N by metric" query returned rows whose
 * metric is entirely NULL — otherwise the model says "no data" while the UI
 * shows a populated table, which reads as a contradiction.
 */
export function detectAllNullColumns(result: ExecuteQueryResponse): string[] {
  if (result.rows.length === 0 || result.columns.length === 0) return [];
  const out: string[] = [];
  for (let i = 0; i < result.columns.length; i += 1) {
    const allNull = result.rows.every((row) => {
      const v = row[i];
      return v === null || v === undefined;
    });
    if (allNull) {
      const name = result.columns[i];
      if (name) out.push(name);
    }
  }
  return out;
}

function renderPreview(result: ExecuteQueryResponse): string {
  if (result.columns.length === 0 || result.rows.length === 0) {
    return '(empty result set)';
  }
  const header = result.columns.join(' | ');
  const lines = result.rows
    .slice(0, MAX_PREVIEW_ROWS)
    .map((row) => row.map((cell) => formatCell(cell)).join(' | '));
  return [header, '-'.repeat(Math.min(header.length, 120)), ...lines].join('\n');
}

function formatCell(v: unknown): string {
  if (v === null || v === undefined) return 'null';
  if (typeof v === 'object') {
    const json = JSON.stringify(v);
    return json.length > MAX_CELL_CHARS ? `${json.slice(0, MAX_CELL_CHARS - 1)}…` : json;
  }
  const s = String(v);
  return s.length > MAX_CELL_CHARS ? `${s.slice(0, MAX_CELL_CHARS - 1)}…` : s;
}

export function parseSummaryJson(text: string): SummarizerResult | null {
  const stripped = text
    .trim()
    .replace(/^```json\s*/i, '')
    .replace(/^```\s*/i, '')
    .replace(/```\s*$/i, '');
  const start = stripped.indexOf('{');
  const end = stripped.lastIndexOf('}');
  if (start < 0) {
    // Fallback: model emitted plain prose without a JSON envelope.
    const trimmed = stripped.trim();
    return trimmed.length > 0 ? { summary: trimmed, highlights: [], followUps: [] } : null;
  }
  if (end < start) return null;
  try {
    const obj = JSON.parse(stripped.slice(start, end + 1)) as SummaryJson;
    const summary =
      typeof obj.summary === 'string' && obj.summary.trim().length > 0 ? obj.summary.trim() : '';
    if (!summary) return null;
    const highlights = pickStringArray(obj.highlights, MAX_HIGHLIGHTS);
    const followUpsRaw = obj.followUps ?? obj.follow_ups;
    const followUps = sanitizeFollowUps(pickStringArray(followUpsRaw, MAX_FOLLOW_UPS * 2)).slice(
      0,
      MAX_FOLLOW_UPS,
    );
    return { summary, highlights, followUps };
  } catch {
    return null;
  }
}

function pickStringArray(input: unknown, max: number): string[] {
  if (!Array.isArray(input)) return [];
  return input
    .filter((x): x is string => typeof x === 'string' && x.trim().length > 0)
    .map((x) => x.trim())
    .slice(0, max);
}

/**
 * Drop follow-up questions that lean on prior-turn context. Each follow-up is
 * dispatched as a fresh prompt to a stateless LLM, so anaphoric references
 * ("these sales", "the table above") become unanswerable. Anything with bare
 * demonstratives without a concrete noun anchor is rejected. The summarizer
 * prompt also instructs against this, but small/local models often slip — this
 * is the safety net.
 */
export function sanitizeFollowUps(items: string[]): string[] {
  const ANAPHORA_PATTERNS: RegExp[] = [
    // English bare demonstratives + generic referents (no proper noun anchor).
    /\b(these|those|the (above|previous|same|preceding|aforementioned))\b/i,
    /\b(this|that) (query|result|table|row|set|data|list|chart|output|number|count|figure|answer)\b/i,
    /\b(them|the ones (shown|listed|above|returned|displayed))\b/i,
    /\bshown above\b/i,
    /\bin the table\b/i,
    // Italian bare demonstratives + generic referents.
    /\b(questi|queste|tali|i suddetti|le suddette|i precedenti|le precedenti|gli stessi|le stesse)\b/i,
    /\b(questo|quello) (risultato|elenco|insieme|grafico|valore|numero|conteggio|dato)\b/i,
    /\bnella tabella\b/i,
    /\bsopra (citati|mostrati|elencati|riportati)\b/i,
  ];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of items) {
    const q = raw.replace(/\s+/g, ' ').trim();
    if (q.length < 8) continue;
    if (ANAPHORA_PATTERNS.some((re) => re.test(q))) continue;
    const key = q.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(q);
  }
  return out;
}

function deterministicFallback(
  result: ExecuteQueryResponse,
  locale: ResponseLocale | undefined,
): string {
  if (locale === 'it') {
    if (result.rowCount === 0) {
      return "Non ho trovato nulla che corrisponda alla tua domanda. Probabilmente il filtro è troppo stretto, oppure l'etichetta o la proprietà che cerchi non esiste nei dati. Prova a riformulare la richiesta o aggiorna lo schema dal pulsante Refresh.";
    }
    const head = result.rows[0];
    const sample = head ? formatRowInline(result.columns, head) : '';
    const truncatedNote = result.truncated ? ', ma il set è stato troncato' : '';
    if (result.rowCount === 1 && sample) {
      return `Ho trovato un solo risultato: ${sample}.`;
    }
    if (sample) {
      return `Ho trovato ${result.rowCount} risultati${truncatedNote}. Il primo è ${sample}; gli altri sono visibili nella tabella sotto.`;
    }
    return `Ho trovato ${result.rowCount} risultati${truncatedNote}. Dai un'occhiata alla tabella sotto per i dettagli.`;
  }
  if (result.rowCount === 0) {
    return 'I could not find anything matching your question. The filter is probably too narrow, or the label/property you are looking for does not exist in the data. Try rephrasing the question, or refresh the schema.';
  }
  const head = result.rows[0];
  const sample = head ? formatRowInline(result.columns, head) : '';
  const truncatedNote = result.truncated ? ', though the set was truncated' : '';
  if (result.rowCount === 1 && sample) {
    return `I found a single match: ${sample}.`;
  }
  if (sample) {
    return `I found ${result.rowCount} matches${truncatedNote}. The first is ${sample}; you can see the rest in the table below.`;
  }
  return `I found ${result.rowCount} matches${truncatedNote}. Have a look at the table below for the details.`;
}

function formatRowInline(columns: string[], row: unknown[]): string {
  const parts: string[] = [];
  for (let i = 0; i < columns.length && i < 4; i += 1) {
    const value = row[i];
    if (value === null || value === undefined) continue;
    const rendered = formatCell(value);
    if (!rendered || rendered === 'null') continue;
    parts.push(`${columns[i]}: ${rendered}`);
  }
  return parts.join(', ');
}
