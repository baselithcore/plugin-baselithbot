import { describe, expect, it } from 'vitest';
import { Nl2QueryOutputSchema } from './output-schema.js';

describe('Nl2QueryOutputSchema', () => {
  it('parses a complete envelope', () => {
    const r = Nl2QueryOutputSchema.parse({
      query: 'SELECT id FROM accounts LIMIT 5',
      language: 'sql',
      explanation: 'Top 5 by id.',
      joinNotes: ['none'],
      involvedEntities: ['accounts'],
    });
    expect(r.query).toBe('SELECT id FROM accounts LIMIT 5');
    expect(r.language).toBe('sql');
  });

  it('fills missing optional arrays with empty defaults', () => {
    const r = Nl2QueryOutputSchema.parse({
      query: 'MATCH (n) RETURN n LIMIT 5',
      language: 'cypher',
    });
    expect(r.explanation).toBe('');
    expect(r.joinNotes).toEqual([]);
    expect(r.involvedEntities).toEqual([]);
  });

  it('rejects empty query', () => {
    expect(() => Nl2QueryOutputSchema.parse({ query: '', language: 'sql' })).toThrow();
  });

  it('rejects unknown language', () => {
    expect(() => Nl2QueryOutputSchema.parse({ query: 'x', language: 'graphql' })).toThrow();
  });

  it('accepts every supported language', () => {
    for (const lang of [
      'sql',
      'soql',
      'cypher',
      'qdrant',
      'mongodb',
      'elasticsearch',
      'redis',
    ] as const) {
      expect(() => Nl2QueryOutputSchema.parse({ query: 'q', language: lang })).not.toThrow();
    }
  });
});
