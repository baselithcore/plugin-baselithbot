import type {
  Dialect,
  Nl2ConversationTurn,
  SchemaGraph,
  PropertyGraphSchema,
  SqlDialect,
  UnifiedSchema,
  VectorStoreSchema,
} from '@dbview/shared';
import { isSaasDialect } from '@dbview/shared';
import { pickFewShotExamples, renderFewShotBlock } from './grounding/few-shot.js';

const SQL_DIALECT_NOTES: Record<SqlDialect, string> = {
  postgres:
    'Use PostgreSQL syntax. Quoted identifiers use double quotes. Use ILIKE for case-insensitive matches.',
  mysql:
    'Use MySQL 8 syntax. Quoted identifiers use backticks. Use LIKE (case-insensitive by default with utf8mb4_*_ci collations).',
  mariadb:
    'Use MariaDB 10+ syntax. Quoted identifiers use backticks. Use LIKE for matches. Avoid features that require MySQL 8 only.',
  mssql:
    'Use T-SQL (SQL Server) syntax. Quoted identifiers use square brackets [name]. Limit results with `SELECT TOP n` or `OFFSET 0 ROWS FETCH NEXT n ROWS ONLY` (do NOT use LIMIT — it is invalid in T-SQL). Use COLLATE for case-insensitive matches when needed.',
  sqlite:
    'Use SQLite syntax. No RIGHT/FULL OUTER JOIN. No window functions older than 3.25. Use LIKE for matches.',
  cockroach:
    'Use CockroachDB SQL (PostgreSQL-compatible). Quoted identifiers use double quotes. Use ILIKE for case-insensitive matches. Prefer indexed columns in WHERE clauses; avoid full table scans on large tables.',
  oracle:
    "Use Oracle SQL (PL/SQL dialect). Quoted identifiers use double quotes. Use UPPER()/LOWER() for case-insensitive matches. Limit results with `FETCH FIRST n ROWS ONLY` (do NOT use LIMIT). Date literals use TO_DATE('YYYY-MM-DD','YYYY-MM-DD').",
  clickhouse:
    'Use ClickHouse SQL. Quoted identifiers use backticks. Use ILIKE for case-insensitive matches. Prefer PREWHERE for selective filters, ORDER BY/LIMIT, and SAMPLE for stats. Use FORMAT clause sparingly. Aggregations are first-class — use uniq()/uniqExact()/quantile() instead of COUNT(DISTINCT) when possible.',
  duckdb:
    'Use DuckDB SQL (PostgreSQL-compatible, OLAP-focused). Quoted identifiers use double quotes. Use ILIKE for case-insensitive matches. Window functions, list/struct/map types, and QUALIFY are available. Prefer columnar-friendly aggregations and avoid SELECT *. Use `read_csv_auto`/`read_parquet` for ad-hoc file reads only when filenames are listed in the schema.',
};

export function compactRelationalSchema(graph: SchemaGraph): string {
  // Salesforce Data Cloud has no SQL schema namespace — entities are referenced
  // bare (e.g. `Account_Home__dll`). Stripping the internal `data_cloud.` prefix
  // from serialization keeps the LLM from inventing schema-qualified references
  // that the SDC Query API rejects with 404 DataSourceEntity not found.
  const isSdc = graph.dialect === 'salesforce-data-cloud';
  const tableRef = (id: string, name: string): string => (isSdc ? name : id);

  const lines: string[] = [];
  for (const t of graph.tables) {
    const cols = t.columns
      .map((c) => {
        const flags: string[] = [];
        if (c.isPrimaryKey) flags.push('PK');
        if (c.isForeignKey) flags.push('FK');
        if (!c.nullable) flags.push('NOT NULL');
        const tag = flags.length ? ` [${flags.join(',')}]` : '';
        const label = c.displayName ? ` — "${c.displayName}"` : '';
        const desc = c.description ? ` (${truncate(c.description, 160)})` : '';
        return `  - ${c.name}: ${c.dataType}${tag}${label}${desc}`;
      })
      .join('\n');
    const tableLabel = t.displayName ? ` — "${t.displayName}"` : '';
    const tableDesc = t.description ? `\n  ${truncate(t.description, 200)}` : '';
    lines.push(`Table ${tableRef(t.id, t.name)}${tableLabel}${tableDesc}\n${cols}`);
  }
  if (graph.edges.length) {
    lines.push('Foreign keys:');
    for (const e of graph.edges) {
      const src = isSdc ? stripSdcSchema(e.source) : e.source;
      const tgt = isSdc ? stripSdcSchema(e.target) : e.target;
      lines.push(`  ${src}.${e.sourceColumn} -> ${tgt}.${e.targetColumn}`);
    }
  }
  return lines.join('\n');
}

function truncate(s: string, max: number): string {
  const clean = s.replace(/\s+/g, ' ').trim();
  return clean.length > max ? `${clean.slice(0, max - 1)}…` : clean;
}

function stripSdcSchema(id: string): string {
  return id.startsWith('data_cloud.') ? id.slice('data_cloud.'.length) : id;
}

export function compactGraphSchema(graph: PropertyGraphSchema): string {
  const lines: string[] = ['Node labels:'];
  for (const l of graph.labels) {
    const props = l.properties
      .map(
        (p) =>
          `  - ${p.name} (type: ${p.types.join('|')}${p.nullable ? '' : ', NOT NULL'})${formatSamples(p.sampleValues)}`,
      )
      .join('\n');
    lines.push(`(:${l.label})${props ? '\n' + props : ''}`);
  }
  if (graph.relationships.length) {
    lines.push('Relationships:');
    for (const r of graph.relationships) {
      lines.push(`  (:${r.source})-[:${r.type}]->(:${r.target})`);
      if (r.properties.length) {
        const propList = r.properties
          .map((p) => `${p.name} (type: ${p.types.join('|')})${formatSamples(p.sampleValues)}`)
          .join(', ');
        lines.push(`    ${r.type} properties: ${propList}`);
      }
    }
  }
  return lines.join('\n');
}

export function compactVectorSchema(graph: VectorStoreSchema): string {
  const lines: string[] = [];
  for (const c of graph.collections) {
    const named = c.namedVectors?.length
      ? `named vectors: [${c.namedVectors.map((v) => `${v.name}(${v.size}d)`).join(', ')}]`
      : `vector: ${c.vectorSize}d ${c.distance}`;
    lines.push(`Collection "${c.name}" — ${named}, points: ${c.pointCount ?? '?'}`);
    if (c.payloadFields.length) {
      lines.push('  payload fields:');
      for (const f of c.payloadFields) {
        lines.push(`    - ${f.name} (${f.types.join('|')})${formatSamples(f.sampleValues)}`);
      }
    }
  }
  return lines.join('\n');
}

function formatSamples(values: string[] | undefined): string {
  if (!values || values.length === 0) return '';
  const quoted = values.map((v) => JSON.stringify(v)).join(', ');
  return ` — observed values: [${quoted}]`;
}

export interface BuildPromptArgs {
  graph: UnifiedSchema;
  dialect: Dialect;
  userPrompt: string;
  rowLimit: number;
  allowDml: boolean;
  retryFeedback?: string;
}

/**
 * `buildSystemPrompt` only depends on `(graph.kind, dialect, allowDml)`; the
 * concrete graph content is never inspected. Caching by stringified key avoids
 * rebuilding the same ~2KB string on every NL2SQL request — relevant when the
 * retry loop runs (up to MAX_RETRIES+1 calls per user prompt).
 */
const systemPromptCache = new Map<string, string>();

export function buildSystemPrompt(
  graph: UnifiedSchema,
  dialect: Dialect,
  allowDml: boolean,
): string {
  const key = `${graph.kind}|${dialect}|${allowDml ? '1' : '0'}`;
  const hit = systemPromptCache.get(key);
  if (hit !== undefined) return hit;
  const text = buildSystemPromptUncached(graph, dialect, allowDml);
  systemPromptCache.set(key, text);
  return text;
}

function buildSystemPromptUncached(
  graph: UnifiedSchema,
  dialect: Dialect,
  allowDml: boolean,
): string {
  const base = buildSystemPromptCore(graph, dialect, allowDml);
  const fewShot = renderFewShotBlock(pickFewShotExamples(dialect));
  return fewShot ? `${base}\n${fewShot}` : base;
}

function buildSystemPromptCore(graph: UnifiedSchema, dialect: Dialect, allowDml: boolean): string {
  if (graph.kind === 'relational' && dialect === 'salesforce-data-cloud') {
    return [
      'You are a careful Salesforce Data Cloud SQL generator. Output ONLY valid JSON matching this TypeScript type:',
      '{ "query": string, "language": "sql", "explanation": string, "joinNotes": string[], "involvedEntities": string[] }',
      '',
      'HARD RULES (violation = invalid response):',
      '- Single SELECT statement only. No semicolons except as terminator.',
      '- NEVER use SELECT *. Always enumerate explicit columns.',
      '- ONLY SELECT statements. No INSERT/UPDATE/DELETE/MERGE — Data Cloud Query API is read-only.',
      '- Never emit DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE, SET, USE.',
      '- Use only entities (DMOs / DLOs / CIOs) and fields present in the provided schema. Reference entities by their bare API name preserving the `__dlm`/`__dll`/`__cio` suffix exactly as shown (e.g. `UnifiedIndividual__dlm`). NEVER prefix with `data_cloud.` or any other schema namespace — Salesforce Data Cloud SQL has no schema concept and the Query API rejects schema-qualified references with `DataSourceEntity not found`. Quote identifiers with double quotes when they contain mixed case or special characters.',
      '- FIELD SELECTION — REASON SEMANTICALLY, NOT BY NAME SIMILARITY. Each schema field may carry a quoted display name (e.g. `- ssot__HireDate__c: date — "Hire Date"`) and an optional description. The display name encodes the business meaning; the technical column name is just a wire identifier. When the user asks about a concept ("hire date", "assunzione", "data di nascita", "income"), pick the field whose display name (or description) matches that concept — DO NOT default to generic system fields like `ssot__CreatedDate__c`, `ssot__LastModifiedDate__c`, `Id__c`, `DataSourceObjectId__c`, etc. unless the user explicitly asked for record-creation or audit metadata. If multiple candidate fields exist, prefer the most specific match and mention the choice in the explanation.',
      '- ENTITY SELECTION — Likewise pick the entity whose display name / description matches the user intent. The same concept may surface across multiple DMOs (e.g. Individual vs Employee vs Contact); choose the one most aligned with the asked entity type rather than the first match by suffix.',
      '- If no field/entity in the schema covers the asked concept, OMIT that predicate or column and state the gap in the explanation field. NEVER invent a plausible-sounding column.',
      '- NEVER invent column names. Every column you reference MUST appear under its entity in the Schema section above. If a column you need is missing, OMIT that predicate/expression and mention the missing field in the explanation — DO NOT guess.',
      "- COLUMN NAMES ARE LITERAL — copy them byte-for-byte from the schema, including their prefix (`ssot__`, `ECH_`, `cdp_`, `KQ_`, etc.) and suffix (`__c`). NEVER strip a prefix to make a name look cleaner (e.g. `Id__c` instead of `ssot__Id__c` is invalid). NEVER translate a name into the user's language (Italian/Spanish/French) — e.g. do NOT invent `Paese__c`, `Citta__c`, `Nome__c`, `Cognome__c`, `Indirizzo__c`. Use the schema's English/technical names verbatim, even when the user prompt is in another language.",
      '- Engine is ANSI SQL (Trino-derived). Available constructs: WITH (CTE), JOIN/LEFT JOIN/RIGHT JOIN/FULL JOIN, GROUP BY, HAVING, ORDER BY, LIMIT, window functions, COALESCE, CASE, CAST.',
      "- String matches: use `LIKE` (case-sensitive) or `LOWER(col) LIKE LOWER('...')` for case-insensitive. ILIKE is NOT supported.",
      "- Date/timestamp filters use ISO literals cast as TIMESTAMP/DATE, e.g. `CAST('2025-01-01' AS DATE)`. Use `date_trunc('day', col)` for bucketing.",
      '- NEVER reference Data Cloud system tables outside the provided schema (no `system.*`).',
      '- LIMIT must be a literal positive integer. Never exceed the rowLimit provided in the user prompt.',
      '- Prefer the smallest set of joins needed. Add a SQL comment above each JOIN explaining the join logic.',
      '- TOP-N RANKING — when ordering by a metric column for "top/highest/biggest/largest/best" or "bottom/lowest/smallest/worst" and applying a LIMIT, ALWAYS add `WHERE <metric> IS NOT NULL` (or include it in an existing WHERE clause). Data Cloud (Trino) defaults to NULLS FIRST on `ORDER BY ... DESC`, so without this filter the top-N rows are the ones where the metric is NULL — useless and misleading.',
      '- Set involvedEntities to the list of entity API names referenced (without quoting).',
      '',
      'JSON ONLY. No markdown fences. No prose outside JSON.',
    ].join('\n');
  }

  if (graph.kind === 'relational' && isSaasDialect(dialect)) {
    return [
      'You are a careful SOQL (Salesforce Object Query Language) generator. Output ONLY valid JSON matching this TypeScript type:',
      '{ "query": string, "language": "soql", "explanation": string, "joinNotes": string[], "involvedEntities": string[] }',
      '',
      'HARD RULES (violation = invalid response):',
      '- Single SOQL SELECT statement only. No semicolons.',
      '- NEVER use SELECT *. Always enumerate explicit fields (Id, Name, ...).',
      '- ONLY SELECT. No INSERT/UPDATE/DELETE/UPSERT/MERGE — those go through REST, not SOQL.',
      '- SOQL has NO JOIN keyword. Traverse relationships with dot notation on lookup fields (e.g. `Account.Owner.Name`) or with parent-child sub-selects (e.g. `SELECT Id, (SELECT Id FROM Contacts) FROM Account`).',
      '- Use ONLY sObjects and fields present in the provided schema. Reference sObjects by their API name without schema prefix (e.g. `Account`, NOT `salesforce.Account`). NEVER invent field names. Every field you reference MUST appear under its sObject in the Schema section above. If a field you need is missing, OMIT that predicate/expression and mention it in the explanation — DO NOT guess.',
      '- Field/object names are case-insensitive on the wire but write them with their canonical CamelCase as listed.',
      '- LIMIT must be a literal positive integer. Never use placeholders. Use the rowLimit value when no explicit count is asked. Never exceed rowLimit.',
      '- Date filters use SOQL literals: `LAST_N_DAYS:7`, `THIS_MONTH`, `YESTERDAY`, etc. ISO datetimes are also accepted (no quotes).',
      '- String literals use single quotes. Identifiers are NEVER quoted.',
      '- Set involvedEntities to the list of sObject API names referenced.',
      '',
      'JSON ONLY. No markdown fences. No prose outside JSON.',
    ].join('\n');
  }

  if (graph.kind === 'relational') {
    const dialectNote =
      dialect in SQL_DIALECT_NOTES
        ? SQL_DIALECT_NOTES[dialect as SqlDialect]
        : SQL_DIALECT_NOTES.postgres;
    return [
      'You are a careful SQL generator. Output ONLY valid JSON matching this TypeScript type:',
      '{ "query": string, "language": "sql", "explanation": string, "joinNotes": string[], "involvedEntities": string[] }',
      '',
      'HARD RULES (violation = invalid response):',
      '- Single SQL statement only. No semicolons except as terminator.',
      '- NEVER use SELECT *. Always enumerate explicit columns.',
      allowDml
        ? '- DML (INSERT/UPDATE/DELETE) is allowed only if user explicitly asked.'
        : '- ONLY SELECT statements. No INSERT/UPDATE/DELETE/MERGE.',
      '- Never emit DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE, SET, USE.',
      '- Use only tables and columns present in the provided schema. NEVER invent column names. Every column you reference MUST appear under its table in the Schema section above. If a column you need is missing, OMIT that predicate/expression and mention the missing field in the explanation field — DO NOT guess a plausible-sounding name.',
      '- Always reference tables with their full schema-qualified name exactly as shown in the schema (e.g. `shop.customers`, not `customers`). Quote identifiers with double quotes only if they contain special characters or are reserved words.',
      '- NEVER invent WHERE clauses, filter values, or joins that the user did not ask for. Do not add country, status, date, or category filters unless the user explicitly mentioned them. Vague prompts ("top N", "main", "principali", "first", "show some") => no WHERE clause; just SELECT + ORDER BY (when implied by a ranking word) + LIMIT.',
      '- "top/main/best/principali by X" => ORDER BY a meaningful X column DESC. If no metric is given, just LIMIT without ORDER BY.',
      '- TOP-N RANKING — when ordering by a metric column for "top/highest/biggest/largest/best/principali" or "bottom/lowest/smallest/worst", ALWAYS add `WHERE <metric> IS NOT NULL` (or include it in an existing WHERE clause). Otherwise NULL rows can dominate the ranking on engines whose `ORDER BY DESC` defaults to NULLS FIRST (Oracle, Trino-derived). Skip this filter only for aggregates like `COUNT(...)` / `SUM(...)` which never return NULL.',
      '- Prefer the smallest set of joins needed. Do NOT join tables whose columns are not in the SELECT or WHERE.',
      '- Add a SQL comment line above each JOIN explaining the join logic, like: -- JOIN orders on customers.id = orders.customer_id (1 customer -> N orders).',
      '- LIMIT must be a literal positive integer. NEVER write `LIMIT N`, `LIMIT <n>`, `LIMIT ?`, or any placeholder. If the question states a number ("3 customers" => LIMIT 3, "first 5 orders" => LIMIT 5), use it. Otherwise use the rowLimit value provided in the user prompt. Never exceed rowLimit.',
      '- All identifiers, literals and operators in the query MUST be concrete and parseable. NEVER emit placeholders like `<column>`, `<value>`, `?`, `:param`, `$1`, `TODO`, or ellipsis (`...`). If a value is unknown, OMIT the predicate.',
      '- Output ONLY tables and columns enumerated under "Allowed entities" in the user prompt. Anything else is forbidden.',
      '- If the question asks about an entity that is NOT in the schema (e.g. user mentions "customers" but no customers table exists), DO NOT invent a table. Instead emit a query against the closest matching real table from the schema and explain the mapping in the explanation field.',
      `- Dialect: ${dialect}. ${dialectNote}`,
      '',
      'JSON ONLY. No markdown fences. No prose outside JSON.',
    ].join('\n');
  }

  if (graph.kind === 'vector') {
    return [
      'You are a careful Qdrant query generator. Output ONLY valid JSON matching this TypeScript type:',
      '{ "query": string, "language": "qdrant", "explanation": string, "joinNotes": string[], "involvedEntities": string[] }',
      '',
      'The "query" field MUST itself be a JSON string encoding a Qdrant op envelope. Supported envelopes:',
      '  {"op":"collections"}',
      '  {"op":"count","collection":"<name>","filter":{...}}',
      '  {"op":"scroll","collection":"<name>","limit":<n>,"filter":{...},"withPayload":true}',
      '  {"op":"search","collection":"<name>","vector":[...],"limit":<n>,"filter":{...}}',
      '',
      'HARD RULES (violation = invalid response):',
      '- Read-only ops only: collections, count, scroll, search. NEVER upsert/delete/create/update/recreate.',
      '- "collection" MUST be a name listed in the schema.',
      '- For "how many" / "quante" / counting questions → use op=count. RETURN only count.',
      '- For "find points where ..." / "show some points" → use op=scroll.',
      '- For semantic similarity with a known vector → op=search (only when the user supplies a vector — otherwise prefer scroll/count).',
      '- "filter" follows Qdrant filter syntax: {"must":[{"key":"<payload_field>","match":{"value":"x"}}]}. For substring/text match on indexed text fields use {"match":{"text":"x"}}.',
      '- TEXT-SEARCH QUESTIONS ("quante volte compare la parola X", "find docs about X", "cita X"): build filter on a text-bearing payload field present in the schema (text, content, body, title, description). Pattern: {"must":[{"key":"<field>","match":{"text":"X"}}]}. Use the LITERAL term from the question, lowercase. If multiple text fields exist, prefer "text" or "content" over "title".',
      '- Pick payload field names ONLY from the schema for the chosen collection. NEVER invent.',
      '- LIMIT must respect the rowLimit provided. If user asks for "first N" / "primi N", set limit accordingly. For op=count, limit is irrelevant — omit it.',
      '- Set involvedEntities to [collection_name].',
      '- Output the inner Qdrant envelope as a JSON string, not as a nested object: e.g. "query": "{\\"op\\":\\"count\\",\\"collection\\":\\"llm-wiki\\",\\"filter\\":{\\"must\\":[{\\"key\\":\\"text\\",\\"match\\":{\\"text\\":\\"terremoto\\"}}]}}"',
      '',
      'JSON ONLY. No markdown fences. No prose outside JSON.',
    ].join('\n');
  }

  if (graph.kind === 'document') {
    return [
      'You are a careful MongoDB query generator. Output ONLY valid JSON matching this TypeScript type:',
      '{ "query": string, "language": "mongodb", "explanation": string, "joinNotes": string[], "involvedEntities": string[] }',
      '',
      'The "query" field MUST be a JSON string encoding a Mongo envelope. Supported envelopes:',
      '  {"op":"collections"}',
      '  {"op":"count","collection":"<name>","filter":{...}}',
      '  {"op":"find","collection":"<name>","filter":{...},"projection":{...},"sort":{...},"limit":N,"skip":N}',
      '  {"op":"distinct","collection":"<name>","field":"<path>","filter":{...}}',
      '  {"op":"aggregate","collection":"<name>","pipeline":[...]}',
      '  {"op":"indexes","collection":"<name>"}',
      '  {"op":"stats","collection":"<name>"}',
      '',
      'HARD RULES (violation = invalid response):',
      '- Read-only ops only. NEVER use $out, $merge, $function, $accumulator, $where in aggregate pipelines.',
      '- "collection" MUST be one of the collections listed in the schema.',
      '- Use ONLY field paths listed in the schema for the chosen collection. NEVER invent fields.',
      '- For "how many" / count questions → op=count. Do not use find just to count.',
      '- For text/regex search → use {"<field>":{"$regex":"x","$options":"i"}} on string fields.',
      '- For date range → use {"<field>":{"$gte":...,"$lt":...}}.',
      '- limit must respect the rowLimit. Default = rowLimit. Never exceed rowLimit.',
      '- Set involvedEntities to [collection_name].',
      '- Output the inner envelope as a JSON string, not a nested object.',
      '',
      'JSON ONLY. No markdown fences. No prose outside JSON.',
    ].join('\n');
  }

  if (graph.kind === 'search') {
    return [
      'You are a careful Elasticsearch query generator. Output ONLY valid JSON matching this TypeScript type:',
      '{ "query": string, "language": "elasticsearch", "explanation": string, "joinNotes": string[], "involvedEntities": string[] }',
      '',
      'The "query" field MUST be a JSON string encoding an envelope. Supported envelopes:',
      '  {"op":"indices"}',
      '  {"op":"count","index":"<name>","query":{...}}',
      '  {"op":"search","index":"<name>","body":{"query":{...},"size":N,"sort":[...],"aggs":{...},"_source":[...]}}',
      '  {"op":"mapping","index":"<name>"}',
      '  {"op":"get","index":"<name>","id":"<doc-id>"}',
      '',
      'HARD RULES (violation = invalid response):',
      '- Read-only ops only. NEVER use update_by_query / delete_by_query / reindex / scripts.',
      '- "index" MUST be one of the indices listed in the schema.',
      '- Body keys allowed: query, size, from, sort, aggs/aggregations, _source, track_total_hits, highlight, fields, min_score. NEVER include `script` or `scripts`.',
      '- For "how many" / "count" questions → op=count with optional query filter. Do NOT use op=search just to count.',
      '- For text search ("find docs about X", "documents mentioning X") → op=search with {"query":{"match":{"<text-field>":"X"}}}. Pick the field from the schema (prefer `text`, `content`, `body`, `title`, `description`).',
      '- For exact term match on keyword field → {"term":{"<keyword-field>":"value"}}.',
      '- For date ranges → {"range":{"<date-field>":{"gte":"now-30d/d"}}}.',
      '- Use ONLY field names listed in the schema for the chosen index. NEVER invent.',
      '- size must respect the rowLimit provided. Default = rowLimit.',
      '- Set involvedEntities to [index_name].',
      '- Output the inner envelope as a JSON string, not nested object.',
      '',
      'JSON ONLY. No markdown fences. No prose outside JSON.',
    ].join('\n');
  }

  if (graph.kind === 'keyvalue') {
    return [
      'You are a careful Redis command generator. Output ONLY valid JSON matching this TypeScript type:',
      '{ "query": string, "language": "redis", "explanation": string, "joinNotes": string[], "involvedEntities": string[] }',
      '',
      'The "query" field MUST be a single Redis command line, e.g. `SCAN 0 MATCH user:* COUNT 100` or `HGETALL user:1`.',
      '',
      'HARD RULES (violation = invalid response):',
      '- Single read-only command only. No semicolons. No newlines inside the command.',
      '- Allowed commands: GET, MGET, EXISTS, TYPE, TTL, OBJECT, KEYS, SCAN, DBSIZE, INFO, PING, HGET, HMGET, HGETALL, HKEYS, HVALS, HLEN, HEXISTS, HSCAN, LRANGE, LLEN, LINDEX, SMEMBERS, SCARD, SISMEMBER, SINTER, SUNION, SDIFF, SSCAN, ZRANGE, ZRANGEBYSCORE, ZSCORE, ZCARD, ZCOUNT, ZRANK, ZSCAN, XLEN, XRANGE, XINFO, BITCOUNT, GETBIT, PFCOUNT.',
      '- NEVER use SET, DEL, FLUSHDB, FLUSHALL, RENAME, COPY, MIGRATE, EXPIRE, PERSIST, CONFIG SET, DEBUG, SHUTDOWN, BGSAVE, SAVE, SLAVEOF, REPLICAOF, CLUSTER, ACL SET, FUNCTION, EVAL, EVALSHA, SCRIPT.',
      '- Use only key patterns matching the namespaces in the schema. Prefer SCAN over KEYS for production data.',
      '- Set involvedEntities to the list of namespace patterns the command targets (e.g. ["user:*"]).',
      '',
      'JSON ONLY. No markdown fences. No prose outside JSON.',
    ].join('\n');
  }

  const engineNote =
    dialect === 'falkordb'
      ? 'Engine: FalkorDB (Cypher subset). Avoid Neo4j-only procedures (apoc.*, db.schema.*). Stick to MATCH, OPTIONAL MATCH, WHERE, WITH, RETURN, ORDER BY, SKIP, LIMIT, UNION, UNWIND.'
      : dialect === 'ultipa'
        ? 'Engine: Ultipa v6 (full GQL/ISO-GQL). Use MATCH, OPTIONAL MATCH, WHERE, WITH, RETURN, ORDER BY, SKIP, LIMIT, UNION, UNWIND, CALL (read procs only). Backtick-quote label/property names with non-alphanumeric characters. Do NOT use apoc.* or db.schema.* — those are Neo4j-only. NEVER use `count(*)` — Ultipa GQL rejects the `*` wildcard. Always count a bound variable: `count(n)`, `count(r)`, or `count(DISTINCT n)`.'
        : 'Engine: Neo4j 5+.';
  return [
    `You are a careful Cypher generator. Output ONLY valid JSON matching this TypeScript type:`,
    '{ "query": string, "language": "cypher", "explanation": string, "joinNotes": string[], "involvedEntities": string[] }',
    '',
    'HARD RULES (violation = invalid response):',
    '- Read-only Cypher only. Use MATCH / OPTIONAL MATCH / WITH / WHERE / RETURN / ORDER BY / SKIP / LIMIT / UNION / UNWIND / CALL (read procs only).',
    '- NEVER use CREATE, DELETE, DETACH, MERGE, SET, REMOVE, DROP, LOAD CSV, FOREACH.',
    '- NEVER call write/admin procedures (apoc.create, apoc.merge, apoc.refactor, apoc.load, apoc.export, apoc.periodic, db.create, db.drop, dbms.*).',
    '- Single statement. No semicolons.',
    '- The query MUST end with a RETURN clause (or UNION whose last branch RETURNs). Never end with WITH/ORDER BY/LIMIT — those are mid-query clauses.',
    '- ORDER BY and LIMIT belong AFTER the final RETURN, not after a trailing WITH.',
    '- Use only labels and relationship types present in the provided schema.',
    '- Property type annotations in the schema (e.g. `(type: STRING)`) are DESCRIPTIVE only. NEVER write them as filter values. Property filters take literal values, e.g. `{status: "paid"}` — not `{status: STRING}`.',
    '- When a property lists "observed values: [...]", you MUST pick filter values from that list. Do NOT invent plausible-sounding values not present.',
    '- Use ONLY property names listed in the schema for the relevant label/relationship. NEVER invent properties (e.g. `createdAt`, `timestamp`, `updatedAt`) that are not present. If the user asks for a time/date filter and no timestamp property exists, OMIT that filter and mention the limitation in the explanation field.',
    '- TEXT-SEARCH QUESTIONS ("how many times X is mentioned", "find pages about X", "quante volte X", "cita X"): use case-insensitive CONTAINS over the text-bearing properties present in the schema (e.g. title, name, content, body, text, description, summary, tags). Pattern: `WHERE toLower(n.title) CONTAINS toLower("X") OR toLower(n.tags) CONTAINS toLower("X")`. Use the LITERAL search term from the question — never invent label values like "concept" or "entity".',
    '- OPEN-ENDED CONTENT QUESTIONS ("what are these about", "what topics", "summarize", "di cosa parlano", "argomenti", "di che parlano i documenti"): DO NOT add a WHERE filter. Just MATCH the relevant nodes and RETURN their text-bearing properties (title, name, body, text, content, description, summary, tags) up to LIMIT. The downstream summarizer extracts topics from the rows. Pattern: `MATCH (n:Page) RETURN n.title AS title, n.text AS text LIMIT 50`.',
    '- COUNT QUESTIONS: for "how many" use `RETURN count(<var>) AS total` where `<var>` is a node or relationship variable bound earlier in the query (e.g. `count(n)`, `count(DISTINCT n)`). NEVER write `count(*)` — Ultipa GQL parses `*` as a syntax error. Do NOT add ORDER BY on a single-row aggregate.',
    '- When the schema has only one node label, do NOT add filters on properties whose values you cannot derive from the question or from sampleValues. Default to the simplest match.',
    '- For every relationship traversed, add a comment line in joinNotes like: "Traverse (:Customer)-[:PLACED]->(:Order) (1 customer -> N orders)".',
    '- Always include LIMIT.',
    '- Set involvedEntities to the list of node labels referenced.',
    `- ${engineNote}`,
    '',
    'JSON ONLY. No markdown fences. No prose outside JSON.',
  ].join('\n');
}

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

/**
 * Schema serialization + allowed-entities enumeration are O(tables × columns)
 * and produce strings that exceed 50KB on wide schemas. They depend only on
 * the graph object identity (SchemaService reuses the same reference for the
 * lifetime of a cache entry), so a WeakMap keyed on the graph yields a free
 * cache that auto-evicts when the schema cache replaces the graph.
 */
interface SchemaPromptContext {
  schemaText: string;
  allowedEntities: string;
}

const schemaContextCache = new WeakMap<UnifiedSchema, SchemaPromptContext>();

function getSchemaPromptContext(graph: UnifiedSchema): SchemaPromptContext {
  let ctx = schemaContextCache.get(graph);
  if (ctx) return ctx;
  const schemaText =
    graph.kind === 'relational'
      ? compactRelationalSchema(graph)
      : graph.kind === 'graph'
        ? compactGraphSchema(graph)
        : graph.kind === 'vector'
          ? compactVectorSchema(graph)
          : graph.kind === 'keyvalue'
            ? compactKeyValueSchema(graph)
            : graph.kind === 'search'
              ? compactSearchSchema(graph)
              : compactDocumentSchema(graph);
  const allowedEntities = listAllowedEntities(graph);
  ctx = { schemaText, allowedEntities };
  schemaContextCache.set(graph, ctx);
  return ctx;
}

export function buildUserPromptBase(args: Omit<BuildPromptArgs, 'retryFeedback'>): UserPromptBase {
  const { schemaText, allowedEntities } = getSchemaPromptContext(args.graph);
  const text = [
    '## Schema',
    schemaText,
    '',
    '## Allowed entities (use ONLY these names, exact case)',
    allowedEntities,
    '',
    '## User question',
    args.userPrompt,
    '',
    '## Constraints',
    `- Row limit: ${args.rowLimit}`,
    `- Allow writes: ${args.allowDml}`,
    '- LIMIT must be a literal integer (e.g. `LIMIT 100`), never a placeholder.',
    '- Reference only the entities listed under "Allowed entities" above.',
  ].join('\n');
  return { text };
}

export function withRetryFeedback(base: UserPromptBase, retryFeedback: string | undefined): string {
  if (!retryFeedback) return base.text;
  return [
    base.text,
    '',
    '## Previous attempt rejected',
    retryFeedback,
    '',
    'Fix the issue and retry. Stay strictly within the allowed entities.',
  ].join('\n');
}

/**
 * Cap per turn-field to keep the prompt budget bounded even if the client
 * forgets to trim before send. The validator already caps the array length;
 * these caps protect against pathologically long single turns.
 */
const HISTORY_PROMPT_MAX_CHARS = 320;
const HISTORY_QUERY_MAX_CHARS = 600;

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
export function renderHistoryBlock(history: readonly Nl2ConversationTurn[] | undefined): string {
  if (!history || history.length === 0) return '';
  const lines: string[] = ['## Prior conversation (most recent last)'];
  history.forEach((turn, idx) => {
    const n = idx + 1;
    const prompt = truncateInline(turn.prompt, HISTORY_PROMPT_MAX_CHARS);
    lines.push(`Turn ${n} user: ${prompt}`);
    if (turn.query) {
      const lang = turn.language ?? 'sql';
      const q = truncateInline(turn.query, HISTORY_QUERY_MAX_CHARS);
      const rows =
        turn.rowCount === undefined || turn.rowCount === null ? '' : ` (rows=${turn.rowCount})`;
      const status = turn.ok === false ? ' [failed]' : '';
      lines.push(`Turn ${n} assistant ${lang}${status}${rows}: ${q}`);
    }
  });
  lines.push('');
  lines.push(
    'Treat the current user question as a follow-up to the turns above. Resolve references ("these", "those", "previous", "now", "also", "instead", "il precedente", "questi") against the most recent turns. Re-generate the full query from scratch — do NOT copy the prior query verbatim; apply the modification asked by the new question. If the new question is unrelated, ignore the history.',
  );
  return lines.join('\n');
}

function truncateInline(s: string, max: number): string {
  const flat = s.replace(/\s+/g, ' ').trim();
  return flat.length > max ? `${flat.slice(0, max - 1)}…` : flat;
}

export function buildUserPrompt(args: BuildPromptArgs): string {
  const base = buildUserPromptBase(args);
  return withRetryFeedback(base, args.retryFeedback);
}

function listAllowedEntities(graph: UnifiedSchema): string {
  if (graph.kind === 'relational') {
    return graph.tables.map((t) => `- ${t.id}`).join('\n');
  }
  if (graph.kind === 'graph') {
    const labels = graph.labels.map((l) => `- (:${l.label})`);
    const rels = graph.relationships.map((r) => `- (:${r.source})-[:${r.type}]->(:${r.target})`);
    return [...labels, ...rels].join('\n');
  }
  if (graph.kind === 'vector') {
    return graph.collections.map((c) => `- ${c.name}`).join('\n');
  }
  if (graph.kind === 'keyvalue') {
    return graph.namespaces.map((n) => `- ${n.pattern}`).join('\n');
  }
  if (graph.kind === 'search') {
    return graph.indices.map((i) => `- ${i.name}`).join('\n');
  }
  return graph.collections.map((c) => `- ${c.name}`).join('\n');
}

export function compactDocumentSchema(graph: Extract<UnifiedSchema, { kind: 'document' }>): string {
  const lines: string[] = [`MongoDB database: ${graph.database}`];
  for (const c of graph.collections) {
    lines.push(
      `Collection "${c.name}" — docs: ${c.docCount ?? '?'}${
        c.indexes.length ? `, indexes: [${c.indexes.join(', ')}]` : ''
      }`,
    );
    for (const f of c.fields.slice(0, 30)) {
      const samples =
        f.sampleValues && f.sampleValues.length
          ? ` — values: [${f.sampleValues.map((v) => JSON.stringify(v)).join(', ')}]`
          : '';
      lines.push(
        `  - ${f.name}: ${f.types.join('|')}${
          f.presence !== undefined ? ` (${Math.round(f.presence * 100)}%)` : ''
        }${samples}`,
      );
    }
    if (c.fields.length > 30) lines.push(`  … +${c.fields.length - 30} more fields`);
  }
  return lines.join('\n');
}

export function compactSearchSchema(graph: Extract<UnifiedSchema, { kind: 'search' }>): string {
  const lines: string[] = [];
  if (graph.cluster) lines.push(`Cluster: ${graph.cluster}`);
  for (const idx of graph.indices) {
    const sizeKB = idx.sizeBytes ? `${Math.round(idx.sizeBytes / 1024)}KB` : '?';
    lines.push(
      `Index "${idx.name}" — docs: ${idx.docCount ?? '?'}, size: ${sizeKB}${
        idx.aliases.length ? `, aliases: [${idx.aliases.join(', ')}]` : ''
      }`,
    );
    for (const f of idx.fields.slice(0, 40)) {
      lines.push(`  - ${f.name}: ${f.type}${f.analyzed ? ' (analyzed)' : ''}`);
    }
    if (idx.fields.length > 40) lines.push(`  … +${idx.fields.length - 40} more fields`);
  }
  return lines.join('\n');
}

export function compactKeyValueSchema(graph: Extract<UnifiedSchema, { kind: 'keyvalue' }>): string {
  const lines: string[] = [`Redis DB ${graph.db} — ${graph.totalKeys} keys observed`];
  for (const n of graph.namespaces) {
    const types = n.types.length ? n.types.join('|') : '?';
    const samples = n.sampleKeys.length
      ? ` examples: [${n.sampleKeys.slice(0, 4).join(', ')}]`
      : '';
    lines.push(`  ${n.pattern} — ${n.keyCount} keys, types: ${types}${samples}`);
  }
  return lines.join('\n');
}
