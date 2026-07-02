import { describe, expect, it } from 'vitest';
import { parseExplainerJson } from './explainer.js';

describe('parseExplainerJson', () => {
  it('parses a clean JSON response', () => {
    const out = parseExplainerJson(
      '{"explanation":"Returns the top 3 customers.","joinNotes":["JOIN orders on customers.id = orders.customer_id"]}',
    );
    expect(out.explanation).toBe('Returns the top 3 customers.');
    expect(out.joinNotes).toEqual(['JOIN orders on customers.id = orders.customer_id']);
  });

  it('strips markdown fences', () => {
    const out = parseExplainerJson(
      '```json\n{"explanation":"Lists customers.","joinNotes":[]}\n```',
    );
    expect(out.explanation).toBe('Lists customers.');
    expect(out.joinNotes).toEqual([]);
  });

  it('returns empty result on malformed JSON', () => {
    expect(parseExplainerJson('not json')).toEqual({ explanation: '', joinNotes: [] });
    expect(parseExplainerJson('{ broken')).toEqual({ explanation: '', joinNotes: [] });
  });

  it('drops non-string joinNotes entries', () => {
    const out = parseExplainerJson(
      '{"explanation":"x","joinNotes":["valid", null, 42, "also valid", ""]}',
    );
    expect(out.joinNotes).toEqual(['valid', 'also valid']);
  });
});
