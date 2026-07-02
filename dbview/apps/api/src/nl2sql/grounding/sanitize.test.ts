import { describe, it, expect } from 'vitest';
import { sanitize } from './sanitize.js';

describe('sanitize SQL', () => {
  const opts = { rowLimit: 100, language: 'sql' as const };

  it('rewrites LIMIT N to numeric LIMIT', () => {
    const r = sanitize('SELECT id FROM t LIMIT N', opts);
    expect(r.query).toBe('SELECT id FROM t LIMIT 100');
    expect(r.fixes).toContain('LIMIT N → LIMIT 100');
  });

  it('rewrites LIMIT <n> placeholder', () => {
    const r = sanitize('SELECT id FROM t LIMIT <n>', opts);
    expect(r.query).toBe('SELECT id FROM t LIMIT 100');
  });

  it('rewrites LIMIT ? placeholder', () => {
    const r = sanitize('SELECT id FROM t LIMIT ?', opts);
    expect(r.query).toBe('SELECT id FROM t LIMIT 100');
  });

  it('rewrites OFFSET placeholder to 0', () => {
    const r = sanitize('SELECT id FROM t LIMIT 10 OFFSET M', opts);
    expect(r.query).toBe('SELECT id FROM t LIMIT 10 OFFSET 0');
  });

  it('rewrites T-SQL TOP placeholder', () => {
    const r = sanitize('SELECT TOP N id FROM t', opts);
    expect(r.query).toBe('SELECT TOP 100 id FROM t');
  });

  it('rewrites T-SQL FETCH NEXT placeholder', () => {
    const r = sanitize('SELECT id FROM t OFFSET 0 ROWS FETCH NEXT N ROWS ONLY', opts);
    expect(r.query).toBe('SELECT id FROM t OFFSET 0 ROWS FETCH NEXT 100 ROWS ONLY');
  });

  it('preserves numeric LIMIT', () => {
    const r = sanitize('SELECT id FROM t LIMIT 5', opts);
    expect(r.query).toBe('SELECT id FROM t LIMIT 5');
    expect(r.fixes).toEqual([]);
  });

  it('strips trailing ellipsis', () => {
    const r = sanitize('SELECT id FROM t LIMIT 5 ...', opts);
    expect(r.query).toBe('SELECT id FROM t LIMIT 5');
    expect(r.fixes).toContain('removed trailing ellipsis');
  });

  it('strips trailing stray single letter after numeric LIMIT', () => {
    const r = sanitize('SELECT brand_name FROM Brands LIMIT 100 N', opts);
    expect(r.query).toBe('SELECT brand_name FROM Brands LIMIT 100');
    expect(r.fixes.some((f) => f.includes('stray'))).toBe(true);
  });

  it('strips trailing stray letter with semicolon', () => {
    const r = sanitize('SELECT id FROM t LIMIT 5 N;', opts);
    expect(r.query).toBe('SELECT id FROM t LIMIT 5;');
  });
});

describe('sanitize SQLite schema prefixes', () => {
  const knownTables = new Set(['Brands', 'Models', 'Customers']);
  const opts = {
    rowLimit: 100,
    language: 'sql' as const,
    knownTables,
    stripAllSchemaPrefixes: true,
  };

  it('strips bogus main. prefix on SQLite tables', () => {
    const r = sanitize('SELECT brand_id FROM main.Brands LIMIT 10', opts);
    expect(r.query).toBe('SELECT brand_id FROM Brands LIMIT 10');
    expect(r.fixes.some((f) => f.includes('stripped bogus prefix "main."'))).toBe(true);
  });

  it('strips bogus prefix in JOIN', () => {
    const r = sanitize(
      'SELECT b.brand_id FROM main.Brands b JOIN main.Models m ON b.brand_id = m.brand_id',
      opts,
    );
    expect(r.query).not.toContain('main.');
  });

  it('does not strip prefix when prefix.table is itself a known table id', () => {
    const known = new Set(['shop.Brands', 'shop.Models']);
    const r = sanitize('SELECT id FROM shop.Brands LIMIT 5', {
      rowLimit: 100,
      language: 'sql',
      knownTables: known,
      stripAllSchemaPrefixes: false,
    });
    expect(r.query).toBe('SELECT id FROM shop.Brands LIMIT 5');
  });

  it('leaves unrelated dotted refs alone', () => {
    const r = sanitize('SELECT b.brand_name FROM Brands b LIMIT 5', opts);
    expect(r.query).toBe('SELECT b.brand_name FROM Brands b LIMIT 5');
  });

  it('collapses spaced dots in qualified identifiers', () => {
    const r = sanitize('SELECT Brands . brand_id FROM Brands LIMIT 5', opts);
    expect(r.query).toContain('Brands.brand_id');
    expect(r.fixes.some((f) => f.includes('spaced dot'))).toBe(true);
  });

  it('strips trailing standalone dot', () => {
    const r = sanitize('SELECT brand_id FROM Brands LIMIT 5 .', opts);
    expect(r.query).toBe('SELECT brand_id FROM Brands LIMIT 5');
  });
});

describe('sanitize SQL — top-N NULL guard', () => {
  const opts = { rowLimit: 100, language: 'sql' as const };

  it('injects IS NOT NULL when ORDER BY metric DESC LIMIT n has no WHERE', () => {
    const r = sanitize('SELECT id, name, total FROM accounts ORDER BY total DESC LIMIT 5', opts);
    expect(r.query).toBe(
      'SELECT id, name, total FROM accounts WHERE total IS NOT NULL ORDER BY total DESC LIMIT 5',
    );
    expect(r.fixes.some((f) => f.includes('IS NOT NULL'))).toBe(true);
  });

  it('appends IS NOT NULL to existing WHERE clause', () => {
    const r = sanitize(
      "SELECT id, total FROM accounts WHERE region = 'EU' ORDER BY total DESC LIMIT 5",
      opts,
    );
    expect(r.query).toBe(
      "SELECT id, total FROM accounts WHERE region = 'EU' AND total IS NOT NULL ORDER BY total DESC LIMIT 5",
    );
  });

  it('handles qualified column reference', () => {
    const r = sanitize('SELECT a.id, a.total FROM accounts a ORDER BY a.total DESC LIMIT 10', opts);
    expect(r.query).toContain('WHERE a.total IS NOT NULL');
  });

  it('skips when IS NOT NULL already present on the same column', () => {
    const sql =
      'SELECT id, total FROM accounts WHERE total IS NOT NULL ORDER BY total DESC LIMIT 5';
    const r = sanitize(sql, opts);
    expect(r.query).toBe(sql);
    expect(r.fixes).toEqual([]);
  });

  it('skips when no LIMIT/TOP/FETCH clause is present', () => {
    const sql = 'SELECT id, total FROM accounts ORDER BY total DESC';
    const r = sanitize(sql, opts);
    expect(r.query).toBe(sql);
  });

  it('skips on aggregate ORDER BY expressions', () => {
    const sql =
      'SELECT region, COUNT(*) AS c FROM accounts GROUP BY region ORDER BY COUNT(*) DESC LIMIT 5';
    const r = sanitize(sql, opts);
    expect(r.query).toBe(sql);
  });

  it('skips on queries with CTE to avoid mis-targeting', () => {
    const sql =
      'WITH t AS (SELECT id, total FROM accounts) SELECT id, total FROM t ORDER BY total DESC LIMIT 5';
    const r = sanitize(sql, opts);
    expect(r.query).toBe(sql);
  });

  it('skips on queries with subqueries', () => {
    const sql = 'SELECT id FROM (SELECT id, total FROM accounts) x ORDER BY total DESC LIMIT 5';
    const r = sanitize(sql, opts);
    expect(r.query).toBe(sql);
  });

  it('handles ASC ordering for "bottom N" queries', () => {
    const r = sanitize('SELECT id, total FROM accounts ORDER BY total ASC LIMIT 5', opts);
    expect(r.query).toContain('WHERE total IS NOT NULL');
  });

  it('handles FETCH NEXT n ROWS ONLY (T-SQL)', () => {
    const r = sanitize(
      'SELECT id, total FROM accounts ORDER BY total DESC OFFSET 0 ROWS FETCH NEXT 5 ROWS ONLY',
      opts,
    );
    expect(r.query).toContain('WHERE total IS NOT NULL');
  });

  it('does not double-inject when sanitize is called twice', () => {
    const first = sanitize('SELECT id, total FROM accounts ORDER BY total DESC LIMIT 5', opts);
    const second = sanitize(first.query, opts);
    expect(second.query).toBe(first.query);
    expect(second.fixes).toEqual([]);
  });
});

describe('sanitize Cypher', () => {
  const opts = { rowLimit: 50, language: 'cypher' as const };

  it('rewrites LIMIT placeholder', () => {
    const r = sanitize('MATCH (n) RETURN n LIMIT N', opts);
    expect(r.query).toBe('MATCH (n) RETURN n LIMIT 50');
  });

  it('rewrites SKIP placeholder', () => {
    const r = sanitize('MATCH (n) RETURN n SKIP K LIMIT 10', opts);
    expect(r.query).toBe('MATCH (n) RETURN n SKIP 0 LIMIT 10');
  });

  it('preserves numeric clauses', () => {
    const r = sanitize('MATCH (n) RETURN n LIMIT 25', opts);
    expect(r.query).toBe('MATCH (n) RETURN n LIMIT 25');
    expect(r.fixes).toEqual([]);
  });
});
