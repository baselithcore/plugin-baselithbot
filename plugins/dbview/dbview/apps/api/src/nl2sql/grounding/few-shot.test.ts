import { describe, expect, it } from 'vitest';
import type { Dialect } from '@dbview/shared';
import { pickFewShotExamples, renderFewShotBlock } from './few-shot.js';

describe('pickFewShotExamples', () => {
  it('returns SDC-specific examples for salesforce-data-cloud', () => {
    const ex = pickFewShotExamples('salesforce-data-cloud');
    expect(ex.length).toBeGreaterThan(0);
    expect(ex[0]?.query).toContain('__dll');
    expect(ex.some((e) => e.query.includes('IS NOT NULL'))).toBe(true);
  });

  it('returns T-SQL examples for mssql with no LIMIT keyword', () => {
    const ex = pickFewShotExamples('mssql');
    expect(ex.length).toBeGreaterThan(0);
    expect(ex.some((e) => e.query.includes('TOP'))).toBe(true);
    for (const e of ex) {
      expect(e.query).not.toMatch(/\bLIMIT\b/);
    }
  });

  it('returns Oracle examples using FETCH FIRST', () => {
    const ex = pickFewShotExamples('oracle');
    expect(ex.some((e) => /FETCH\s+FIRST/i.test(e.query))).toBe(true);
    for (const e of ex) {
      expect(e.query).not.toMatch(/\bLIMIT\b/);
    }
  });

  it('returns SOQL examples for salesforce', () => {
    const ex = pickFewShotExamples('salesforce');
    expect(ex.length).toBeGreaterThan(0);
    expect(ex.some((e) => e.query.includes('Owner.Name'))).toBe(true);
  });

  it('returns Cypher examples for graph dialects', () => {
    for (const d of ['neo4j', 'falkordb', 'ultipa'] as const) {
      const ex = pickFewShotExamples(d as Dialect);
      expect(ex.length).toBeGreaterThan(0);
      expect(ex[0]?.query).toMatch(/\bMATCH\b/);
    }
  });

  it('returns generic SQL examples for postgres/mysql/sqlite', () => {
    for (const d of ['postgres', 'mysql', 'sqlite'] as const) {
      const ex = pickFewShotExamples(d as Dialect);
      expect(ex.length).toBeGreaterThan(0);
      expect(ex.some((e) => e.query.includes('LIMIT'))).toBe(true);
    }
  });
});

describe('renderFewShotBlock', () => {
  it('renders Q/A blocks with notes when present', () => {
    const out = renderFewShotBlock([
      { question: 'Top 5 by amount', query: 'SELECT id FROM t LIMIT 5', note: 'top-N' },
    ]);
    expect(out).toContain('Reference examples');
    expect(out).toContain('Q: Top 5 by amount');
    expect(out).toContain('A: SELECT id FROM t LIMIT 5');
    expect(out).toContain('— top-N');
  });

  it('returns empty string when no examples', () => {
    expect(renderFewShotBlock([])).toBe('');
  });
});
