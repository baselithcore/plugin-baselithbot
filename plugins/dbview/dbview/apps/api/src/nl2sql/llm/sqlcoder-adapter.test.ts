import { describe, expect, it } from 'vitest';
import type { SchemaGraph } from '@dbview/shared';
import { extractSql, renderSqlcoderPrompt } from './sqlcoder-adapter.js';

const SCHEMA: SchemaGraph = {
  kind: 'relational',
  dialect: 'postgres',
  generatedAt: '2026-01-01T00:00:00.000Z',
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
          name: 'name',
          dataType: 'text',
          nullable: false,
          isPrimaryKey: false,
          isForeignKey: false,
          isUnique: false,
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
  edges: [
    {
      id: 'fk1',
      source: 'shop.orders',
      sourceColumn: 'customer_id',
      target: 'shop.customers',
      targetColumn: 'id',
    },
  ],
};

describe('extractSql', () => {
  it('returns the SQL when wrapped in markdown fences', () => {
    expect(extractSql('```sql\nSELECT 1;\n```')).toBe('SELECT 1');
  });

  it('strips a leading [SQL] echo', () => {
    expect(extractSql('[SQL]\nSELECT id FROM t;\n')).toBe('SELECT id FROM t');
  });

  it('truncates at the first semicolon to drop trailing prose', () => {
    expect(extractSql('SELECT 1; -- explanation\nignored')).toBe('SELECT 1');
  });

  it('handles plain raw output', () => {
    expect(extractSql('SELECT id, name FROM shop.customers LIMIT 3')).toBe(
      'SELECT id, name FROM shop.customers LIMIT 3',
    );
  });

  it('strips leading prose before SELECT', () => {
    expect(extractSql('Sure, here is the query:\nSELECT id FROM t LIMIT 5')).toBe(
      'SELECT id FROM t LIMIT 5',
    );
  });

  it('returns empty string when no SQL keyword is found', () => {
    expect(extractSql('FROM Brands order by id')).toBe('');
    expect(extractSql('I cannot answer this question.')).toBe('');
  });

  it('drops trailing prose after blank line', () => {
    expect(extractSql('SELECT brand_id FROM Brands LIMIT 5\n\nNote: limit was applied.')).toBe(
      'SELECT brand_id FROM Brands LIMIT 5',
    );
  });

  it('finds SELECT inside a CTE prelude', () => {
    expect(extractSql('WITH t AS (SELECT id FROM x) SELECT * FROM t')).toContain('WITH t AS');
  });
});

describe('renderSqlcoderPrompt', () => {
  it('includes schema-qualified DDL and the user question', () => {
    const prompt = renderSqlcoderPrompt({
      schema: SCHEMA,
      dialect: 'postgres',
      userPrompt: 'top 3 customer names',
      allowDml: false,
      rowLimit: 100,
    });
    expect(prompt).toContain('CREATE TABLE shop.customers');
    expect(prompt).toContain('CREATE TABLE shop.orders');
    expect(prompt).toContain('PRIMARY KEY');
    expect(prompt).toContain('top 3 customer names');
    expect(prompt).toContain('shop.orders.customer_id -> shop.customers.id');
    expect(prompt).toContain('LIMIT 100');
    expect(prompt.endsWith('```sql')).toBe(true);
  });

  it('embeds retry feedback when provided', () => {
    const prompt = renderSqlcoderPrompt({
      schema: SCHEMA,
      dialect: 'postgres',
      userPrompt: 'list customers',
      allowDml: false,
      rowLimit: 100,
      retryFeedback: 'unknown_table: foo',
    });
    expect(prompt).toContain('previous attempt was rejected: unknown_table: foo');
  });
});
