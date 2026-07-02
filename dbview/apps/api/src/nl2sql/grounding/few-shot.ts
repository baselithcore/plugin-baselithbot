import type { Dialect } from '@dbview/shared';

export interface FewShotExample {
  question: string;
  query: string;
  /** Optional one-line note shown above the example to highlight the lesson. */
  note?: string;
}

/**
 * Static few-shot examples appended to the system prompt. They are NOT meant
 * to teach domain knowledge — they teach query SHAPE for the dialect:
 *   - LIMIT vs TOP vs FETCH NEXT placement
 *   - NULL handling on top-N ranking
 *   - WHERE-clause discipline (don't invent filters)
 *   - JOIN comment convention
 *   - count vs scroll vs find for non-SQL engines
 *
 * Examples are deliberately schema-agnostic ("orders.amount", "users.name")
 * so they don't conflict with whatever real schema the validator sees.
 */
const SQL_BASE_EXAMPLES: FewShotExample[] = [
  {
    note: 'Top-N ranking — always exclude NULL on the metric column.',
    question: 'Top 5 orders by amount',
    query:
      '-- exclude null amounts so the ranking is meaningful\nSELECT id, customer_id, amount FROM orders WHERE amount IS NOT NULL ORDER BY amount DESC LIMIT 5',
  },
  {
    note: 'Vague "show some" question — no WHERE, no ORDER BY, just LIMIT.',
    question: 'Show me some customers',
    query: 'SELECT id, name, email FROM customers LIMIT 100',
  },
  {
    note: 'Join — comment the relationship and project only the columns asked.',
    question: 'List the order amount and the customer name for the 10 most recent orders',
    query:
      '-- JOIN customers on orders.customer_id = customers.id (1 customer -> N orders)\nSELECT o.id, o.amount, c.name FROM orders o JOIN customers c ON o.customer_id = c.id WHERE o.created_at IS NOT NULL ORDER BY o.created_at DESC LIMIT 10',
  },
];

const TSQL_EXAMPLES: FewShotExample[] = [
  {
    note: 'T-SQL has no LIMIT — use TOP or FETCH NEXT.',
    question: 'Top 5 orders by amount',
    query:
      'SELECT TOP 5 id, customer_id, amount FROM orders WHERE amount IS NOT NULL ORDER BY amount DESC',
  },
  {
    note: 'Pagination — OFFSET ... FETCH NEXT, never LIMIT.',
    question: 'Show me some customers',
    query:
      'SELECT id, name, email FROM customers ORDER BY id OFFSET 0 ROWS FETCH NEXT 100 ROWS ONLY',
  },
];

const ORACLE_EXAMPLES: FewShotExample[] = [
  {
    note: 'Oracle uses FETCH FIRST, not LIMIT.',
    question: 'Top 5 orders by amount',
    query:
      'SELECT id, customer_id, amount FROM orders WHERE amount IS NOT NULL ORDER BY amount DESC FETCH FIRST 5 ROWS ONLY',
  },
];

const SDC_EXAMPLES: FewShotExample[] = [
  {
    note: 'Bare entity name with __dlm/__dll suffix, no schema prefix. Field names include their prefix exactly as shown in the schema (e.g. `ssot__`, `ECH_`) — never strip prefixes.',
    question: 'Top 5 home accounts by total goal',
    query:
      '-- exclude null goals; Trino orders nulls first on DESC otherwise\nSELECT ssot__Id__c, ssot__Name__c, ECH_TotalGOAL_c__c FROM Account_Home__dll WHERE ECH_TotalGOAL_c__c IS NOT NULL ORDER BY ECH_TotalGOAL_c__c DESC LIMIT 5',
  },
  {
    note: 'Case-insensitive text match — LOWER both sides; ILIKE is unsupported. Keep `ssot__` prefix on standard DMO fields.',
    question: 'Find individuals whose last name contains "rossi"',
    query:
      "SELECT ssot__Id__c, ssot__FirstName__c, ssot__LastName__c FROM ssot__Individual__dlm WHERE LOWER(ssot__LastName__c) LIKE LOWER('%rossi%') LIMIT 100",
  },
  {
    note: 'Italian/localized question — DO NOT translate field names. Use only the literal column names from the schema (e.g. address lives in `ECH_FullAddress_c__c`, not invented `Citta__c`/`Paese__c`).',
    question: 'Quanti dipendenti ci sono nella sede di Rubbiano?',
    query:
      "SELECT COUNT(*) AS total FROM Account_Home__dll WHERE LOWER(ECH_FullAddress_c__c) LIKE LOWER('%Rubbiano%')",
  },
];

const SOQL_EXAMPLES: FewShotExample[] = [
  {
    note: 'SOQL — no JOIN, traverse via dot notation; no SELECT *; LIMIT literal.',
    question: 'List the 10 most recent accounts with their owner name',
    query: 'SELECT Id, Name, Owner.Name FROM Account ORDER BY CreatedDate DESC LIMIT 10',
  },
  {
    note: 'Parent-child sub-select instead of JOIN.',
    question: 'For each account, list its contacts',
    query: 'SELECT Id, Name, (SELECT Id, Name FROM Contacts) FROM Account LIMIT 50',
  },
];

const CYPHER_EXAMPLES: FewShotExample[] = [
  {
    note: 'Top-N — explicit RETURN with ORDER BY DESC LIMIT.',
    question: 'Top 5 customers by order count',
    query:
      'MATCH (c:Customer)-[:PLACED]->(o:Order) RETURN c.name AS name, count(o) AS orders ORDER BY orders DESC LIMIT 5',
  },
  {
    note: 'Text search on title — toLower CONTAINS, never invent label values.',
    question: 'How many pages mention "earthquake"?',
    query:
      'MATCH (n:Page) WHERE toLower(n.title) CONTAINS toLower("earthquake") OR toLower(n.text) CONTAINS toLower("earthquake") RETURN count(n) AS total',
  },
];

const QDRANT_EXAMPLES: FewShotExample[] = [
  {
    note: 'Counting → op=count; never op=scroll just to count.',
    question: 'How many documents mention "earthquake"?',
    query:
      '{"op":"count","collection":"docs","filter":{"must":[{"key":"text","match":{"text":"earthquake"}}]}}',
  },
  {
    note: 'Browse → op=scroll with limit + payload.',
    question: 'Show me 20 documents',
    query: '{"op":"scroll","collection":"docs","limit":20,"withPayload":true}',
  },
];

const MONGO_EXAMPLES: FewShotExample[] = [
  {
    note: 'Counting → op=count.',
    question: 'How many users are active?',
    query: '{"op":"count","collection":"users","filter":{"active":true}}',
  },
  {
    note: 'Top-N → op=find with sort + limit, project only the asked fields.',
    question: 'Top 5 orders by amount',
    query:
      '{"op":"find","collection":"orders","filter":{"amount":{"$ne":null}},"projection":{"_id":1,"customer_id":1,"amount":1},"sort":{"amount":-1},"limit":5}',
  },
];

const ES_EXAMPLES: FewShotExample[] = [
  {
    note: 'Counting → op=count; do not use op=search just to count.',
    question: 'How many documents mention "earthquake"?',
    query: '{"op":"count","index":"docs","query":{"match":{"text":"earthquake"}}}',
  },
  {
    note: 'Browse → op=search with size; project via _source.',
    question: 'Show me 10 documents',
    query: '{"op":"search","index":"docs","body":{"query":{"match_all":{}},"size":10}}',
  },
];

const REDIS_EXAMPLES: FewShotExample[] = [
  {
    note: 'Prefer SCAN over KEYS in production.',
    question: 'List user keys',
    query: 'SCAN 0 MATCH user:* COUNT 100',
  },
  {
    note: 'Read a hash by key.',
    question: 'Show user 42 fields',
    query: 'HGETALL user:42',
  },
];

/**
 * Pick the few-shot bank for a (kind, dialect) pair. Returns an empty array
 * when no curated examples exist — callers must skip rendering rather than
 * fall back to a generic dialect, since cross-dialect examples confuse the
 * model more than they help (e.g. teaching `LIMIT` to a T-SQL prompt).
 */
export function pickFewShotExamples(dialect: Dialect): FewShotExample[] {
  switch (dialect) {
    case 'salesforce-data-cloud':
      return SDC_EXAMPLES;
    case 'salesforce':
      return SOQL_EXAMPLES;
    case 'mssql':
      return TSQL_EXAMPLES;
    case 'oracle':
      return ORACLE_EXAMPLES;
    case 'postgres':
    case 'mysql':
    case 'mariadb':
    case 'sqlite':
    case 'cockroach':
    case 'clickhouse':
    case 'duckdb':
      return SQL_BASE_EXAMPLES;
    case 'neo4j':
    case 'falkordb':
    case 'ultipa':
      return CYPHER_EXAMPLES;
    case 'qdrant':
      return QDRANT_EXAMPLES;
    case 'mongodb':
      return MONGO_EXAMPLES;
    case 'elasticsearch':
      return ES_EXAMPLES;
    case 'redis':
      return REDIS_EXAMPLES;
    default:
      return [];
  }
}

/**
 * Render examples as a single string block ready to append to a system prompt.
 * Returns the empty string when no examples are available so callers can
 * unconditionally concatenate without producing a stray heading.
 */
export function renderFewShotBlock(examples: FewShotExample[]): string {
  if (examples.length === 0) return '';
  const blocks = examples.map((ex, i) => {
    const head = `Example ${i + 1}${ex.note ? ` — ${ex.note}` : ''}`;
    return `${head}\nQ: ${ex.question}\nA: ${ex.query}`;
  });
  return ['', 'Reference examples (style + structure to imitate):', ...blocks].join('\n');
}
