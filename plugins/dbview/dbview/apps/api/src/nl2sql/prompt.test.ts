import { describe, expect, it } from 'vitest';
import type { PropertyGraphSchema, SchemaGraph, VectorStoreSchema } from '@dbview/shared';
import {
  buildSystemPrompt,
  buildUserPrompt,
  compactGraphSchema,
  compactRelationalSchema,
  compactVectorSchema,
  renderHistoryBlock,
} from './prompt.js';

const relational: SchemaGraph = {
  kind: 'relational',
  dialect: 'postgres',
  generatedAt: '2026-01-01T00:00:00.000Z',
  edges: [
    {
      id: 'fk_o_c',
      source: 'shop.orders',
      target: 'shop.customers',
      sourceColumn: 'customer_id',
      targetColumn: 'id',
      constraintName: 'fk_o_c',
    },
  ],
  tables: [
    {
      id: 'shop.customers',
      schema: 'shop',
      name: 'customers',
      columns: [
        {
          name: 'id',
          dataType: 'integer',
          nullable: false,
          isPrimaryKey: true,
          isForeignKey: false,
          isUnique: false,
        },
        {
          name: 'email',
          dataType: 'text',
          nullable: false,
          isPrimaryKey: false,
          isForeignKey: false,
          isUnique: true,
        },
      ],
    },
    {
      id: 'shop.orders',
      schema: 'shop',
      name: 'orders',
      columns: [
        {
          name: 'id',
          dataType: 'integer',
          nullable: false,
          isPrimaryKey: true,
          isForeignKey: false,
          isUnique: false,
        },
        {
          name: 'customer_id',
          dataType: 'integer',
          nullable: false,
          isPrimaryKey: false,
          isForeignKey: true,
          isUnique: false,
        },
      ],
    },
  ],
};

const graph: PropertyGraphSchema = {
  kind: 'graph',
  dialect: 'neo4j',
  generatedAt: '2026-01-01T00:00:00.000Z',
  labels: [
    {
      id: 'Customer',
      label: 'Customer',
      properties: [
        { name: 'id', types: ['INTEGER'], nullable: false },
        { name: 'email', types: ['STRING'], nullable: true, sampleValues: ['a@b', 'c@d'] },
      ],
    },
    {
      id: 'Order',
      label: 'Order',
      properties: [{ name: 'total', types: ['FLOAT'], nullable: true }],
    },
  ],
  relationships: [
    {
      id: 'PLACED',
      type: 'PLACED',
      source: 'Customer',
      target: 'Order',
      properties: [{ name: 'when', types: ['DATE'], nullable: true }],
    },
  ],
};

const vector: VectorStoreSchema = {
  kind: 'vector',
  dialect: 'qdrant',
  generatedAt: '2026-01-01T00:00:00.000Z',
  collections: [
    {
      id: 'docs',
      name: 'docs',
      vectorSize: 1536,
      distance: 'Cosine',
      pointCount: 1000,
      payloadFields: [
        { name: 'title', types: ['string'], sampleValues: ['hello', 'world'] },
        { name: 'text', types: ['string'] },
      ],
    },
  ],
};

describe('compactRelationalSchema', () => {
  it('lists tables and columns with flags', () => {
    const out = compactRelationalSchema(relational);
    expect(out).toContain('Table shop.customers');
    expect(out).toContain('id: integer [PK,NOT NULL]');
    expect(out).toContain('email: text [NOT NULL]');
    expect(out).toContain('customer_id: integer [FK,NOT NULL]');
  });

  it('emits foreign-key block when edges present', () => {
    const out = compactRelationalSchema(relational);
    expect(out).toContain('Foreign keys:');
    expect(out).toContain('shop.orders.customer_id -> shop.customers.id');
  });
});

describe('compactGraphSchema', () => {
  it('lists labels with sample values when present', () => {
    const out = compactGraphSchema(graph);
    expect(out).toContain('(:Customer)');
    expect(out).toContain('email (type: STRING)');
    expect(out).toContain('observed values: ["a@b", "c@d"]');
  });

  it('lists relationships with properties', () => {
    const out = compactGraphSchema(graph);
    expect(out).toContain('(:Customer)-[:PLACED]->(:Order)');
    expect(out).toContain('PLACED properties: when (type: DATE)');
  });
});

describe('compactVectorSchema', () => {
  it('lists collection with vector size and distance', () => {
    const out = compactVectorSchema(vector);
    expect(out).toContain('Collection "docs"');
    expect(out).toContain('vector: 1536d Cosine');
    expect(out).toContain('points: 1000');
  });

  it('lists payload fields with samples', () => {
    const out = compactVectorSchema(vector);
    expect(out).toContain('title (string)');
    expect(out).toContain('observed values: ["hello", "world"]');
  });
});

describe('buildSystemPrompt', () => {
  it('relational prompt mentions dialect note and forbids SELECT *', () => {
    const out = buildSystemPrompt(relational, 'postgres', false);
    expect(out).toMatch(/SELECT \*/i);
    expect(out).toMatch(/Dialect: postgres/);
    expect(out).toMatch(/double quotes/);
  });

  it('relational prompt under mssql warns against LIMIT', () => {
    const out = buildSystemPrompt(relational, 'mssql', false);
    expect(out).toMatch(/T-SQL/);
    expect(out).toMatch(/do NOT use LIMIT/);
  });

  it('relational with allowDml true permits DML wording', () => {
    const out = buildSystemPrompt(relational, 'postgres', true);
    expect(out).toMatch(/DML.*allowed/i);
  });

  it('graph prompt forbids write procs', () => {
    const out = buildSystemPrompt(graph, 'neo4j', false);
    expect(out).toMatch(/Read-only Cypher only/);
    expect(out).toMatch(/NEVER use CREATE/);
  });

  it('graph prompt for ultipa contains engine-specific note', () => {
    const out = buildSystemPrompt(graph, 'ultipa', false);
    expect(out).toMatch(/Ultipa/);
    expect(out).toMatch(/apoc\.\*/);
  });

  it('vector prompt enforces read-only ops + JSON envelope', () => {
    const out = buildSystemPrompt(vector, 'qdrant', false);
    expect(out).toMatch(/Read-only ops only/);
    expect(out).toMatch(/op=count/);
  });
});

describe('buildUserPrompt', () => {
  it('lists allowed entities verbatim', () => {
    const out = buildUserPrompt({
      graph: relational,
      dialect: 'postgres',
      userPrompt: 'top 5 customers',
      rowLimit: 50,
      allowDml: false,
    });
    expect(out).toContain('## Allowed entities');
    expect(out).toContain('- shop.customers');
    expect(out).toContain('- shop.orders');
    expect(out).toContain('Row limit: 50');
  });

  it('includes retry feedback section when provided', () => {
    const out = buildUserPrompt({
      graph: relational,
      dialect: 'postgres',
      userPrompt: 'top 5',
      rowLimit: 50,
      allowDml: false,
      retryFeedback: 'previous SQL used SELECT *',
    });
    expect(out).toContain('## Previous attempt rejected');
    expect(out).toContain('previous SQL used SELECT *');
  });

  it('omits retry section when feedback absent', () => {
    const out = buildUserPrompt({
      graph: relational,
      dialect: 'postgres',
      userPrompt: 'x',
      rowLimit: 10,
      allowDml: false,
    });
    expect(out).not.toContain('## Previous attempt rejected');
  });

  it('graph prompt lists labels and relationships', () => {
    const out = buildUserPrompt({
      graph,
      dialect: 'neo4j',
      userPrompt: 'who bought what',
      rowLimit: 25,
      allowDml: false,
    });
    expect(out).toContain('- (:Customer)');
    expect(out).toContain('- (:Customer)-[:PLACED]->(:Order)');
  });

  it('vector prompt lists collection names', () => {
    const out = buildUserPrompt({
      graph: vector,
      dialect: 'qdrant',
      userPrompt: 'find similar docs',
      rowLimit: 5,
      allowDml: false,
    });
    expect(out).toContain('- docs');
  });
});

describe('renderHistoryBlock', () => {
  it('returns empty string when history is missing or empty', () => {
    expect(renderHistoryBlock(undefined)).toBe('');
    expect(renderHistoryBlock([])).toBe('');
  });

  it('renders each prior turn with prompt + query + row count', () => {
    const out = renderHistoryBlock([
      {
        prompt: 'top 5 customers by spend',
        query: 'SELECT id, name FROM shop.customers ORDER BY spend DESC LIMIT 5',
        language: 'sql',
        rowCount: 5,
        ok: true,
      },
      {
        prompt: 'now only Italy',
        query:
          "SELECT id, name FROM shop.customers WHERE country = 'IT' ORDER BY spend DESC LIMIT 5",
        language: 'sql',
        rowCount: 3,
        ok: true,
      },
    ]);
    expect(out).toContain('## Prior conversation');
    expect(out).toContain('Turn 1 user: top 5 customers by spend');
    expect(out).toContain('Turn 1 assistant sql (rows=5):');
    expect(out).toContain('Turn 2 user: now only Italy');
    expect(out).toContain('Turn 2 assistant sql (rows=3):');
    expect(out).toMatch(/Resolve references/);
  });

  it('marks failed prior turns and omits row count when null', () => {
    const out = renderHistoryBlock([
      {
        prompt: 'bogus query',
        query: 'SELECT bad FROM shop.customers',
        language: 'sql',
        rowCount: null,
        ok: false,
      },
    ]);
    expect(out).toContain('Turn 1 assistant sql [failed]:');
    expect(out).not.toMatch(/rows=/);
  });

  it('omits assistant line when query is absent', () => {
    const out = renderHistoryBlock([{ prompt: 'just a question' }]);
    expect(out).toContain('Turn 1 user: just a question');
    expect(out).not.toMatch(/assistant/);
  });

  it('truncates very long prompts and queries', () => {
    const longPrompt = 'a'.repeat(2000);
    const longQuery = 'SELECT ' + 'col, '.repeat(500) + 'last FROM shop.customers';
    const out = renderHistoryBlock([
      { prompt: longPrompt, query: longQuery, language: 'sql', rowCount: 1, ok: true },
    ]);
    expect(out).toContain('…');
    expect(out.length).toBeLessThan(longPrompt.length + longQuery.length);
  });
});
