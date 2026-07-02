import { describe, expect, it } from 'vitest';
import { SHOP_SCHEMA } from './fixtures/shop-schema.js';
import { SHOP_EVAL_CASES } from './cases/shop-cases.js';
import { renderReport, runEvalCase, summarize } from './runner.js';
import type { EvalCase, RunnerAdapter } from './types.js';

/**
 * Stub adapter: maps each case id to a canned LLM JSON response. The harness
 * is designed to work with any adapter, so the unit suite uses a stub to keep
 * CI deterministic; live-LLM runs are exercised via the CLI script.
 */
function stubAdapter(responses: Record<string, string>): RunnerAdapter {
  const queue = new Map<string, string>(Object.entries(responses));
  let lastKey = '';
  return {
    async complete(_system, user) {
      // Match by user-prompt substring so we can address responses by case id
      // via a sentinel inserted in the prompt of the test.
      for (const [key, value] of queue) {
        if (user.includes(key)) {
          lastKey = key;
          return value;
        }
      }
      throw new Error(`stub adapter: no canned response for prompt; lastKey=${lastKey}`);
    },
  };
}

function envelope(query: string, involved: string[]): string {
  return JSON.stringify({
    query,
    language: 'sql',
    explanation: 'eval',
    joinNotes: [],
    involvedEntities: involved,
  });
}

describe('runEvalCase — happy paths', () => {
  it('passes when canned SQL matches all expectations', async () => {
    const c: EvalCase = {
      id: 'top-customers',
      prompt: 'Top 5 customers by total revenue',
      expectations: {
        mustValidate: true,
        mustInvolveTables: ['shop.customers', 'shop.orders'],
        mustContain: ['order by', 'limit 5'],
        mustNotContain: ['select *'],
      },
    };
    const adapter = stubAdapter({
      'Top 5 customers by total revenue': envelope(
        'SELECT c.id, c.name, SUM(o.total_amount) AS revenue FROM shop.customers c JOIN shop.orders o ON o.customer_id = c.id WHERE o.total_amount IS NOT NULL GROUP BY c.id, c.name ORDER BY revenue DESC LIMIT 5',
        ['shop.customers', 'shop.orders']
      ),
    });
    const r = await runEvalCase(c, SHOP_SCHEMA, adapter);
    expect(r.passed).toBe(true);
    expect(r.reasons).toEqual([]);
    expect(r.involvedTables).toEqual(expect.arrayContaining(['shop.customers', 'shop.orders']));
  });

  it('top-N NULL guard auto-injected by sanitize satisfies mustContain "is not null"', async () => {
    const c: EvalCase = {
      id: 'top-products-by-price',
      prompt: 'Top 5 products by price',
      expectations: {
        mustValidate: true,
        mustInvolveTables: ['shop.products'],
        mustContain: ['is not null', 'limit 5'],
      },
    };
    const adapter = stubAdapter({
      'Top 5 products by price': envelope(
        // The model "forgot" the IS NOT NULL — sanitize must inject it.
        'SELECT id, name, price FROM shop.products ORDER BY price DESC LIMIT 5',
        ['shop.products']
      ),
    });
    const r = await runEvalCase(c, SHOP_SCHEMA, adapter);
    expect(r.passed).toBe(true);
    expect(r.validatedQuery?.toLowerCase()).toContain('is not null');
  });
});

describe('runEvalCase — failure modes', () => {
  it('reports missing table when query touches the wrong entity', async () => {
    const c: EvalCase = {
      id: 'wrong-table',
      prompt: 'How many orders are there?',
      expectations: {
        mustValidate: true,
        mustInvolveTables: ['shop.orders'],
        mustContain: ['count'],
      },
    };
    const adapter = stubAdapter({
      'How many orders are there?': envelope('SELECT COUNT(*) FROM shop.customers', [
        'shop.customers',
      ]),
    });
    const r = await runEvalCase(c, SHOP_SCHEMA, adapter);
    expect(r.passed).toBe(false);
    expect(r.reasons.join(' ')).toContain('missing involved table: shop.orders');
  });

  it('reports forbidden substring when SELECT * leaks through', async () => {
    const c: EvalCase = {
      id: 'no-select-star',
      prompt: 'List products',
      expectations: { mustNotContain: ['select *'] },
    };
    const adapter = stubAdapter({
      'List products': envelope('SELECT * FROM shop.products LIMIT 100', ['shop.products']),
    });
    const r = await runEvalCase(c, SHOP_SCHEMA, adapter);
    expect(r.passed).toBe(false);
  });

  it('falls back to full schema when pruning hides a needed entity', async () => {
    // Prompt mentions only "shipments"; pruning will drop customers + orders.
    // First adapter response references customers (dropped) → unknown_table.
    // Second response uses shipments only → passes.
    let calls = 0;
    const adapter: RunnerAdapter = {
      async complete() {
        calls += 1;
        if (calls === 1) {
          return envelope(
            'SELECT s.id, c.name FROM shop.shipments s JOIN shop.customers c ON c.id = s.id LIMIT 10',
            ['shop.shipments', 'shop.customers']
          );
        }
        return envelope('SELECT id, tracking_number FROM shop.shipments LIMIT 10', [
          'shop.shipments',
        ]);
      },
    };
    const c: EvalCase = {
      id: 'shipments-only',
      prompt: 'List shipments',
      expectations: { mustInvolveTables: ['shop.shipments'] },
    };
    const r = await runEvalCase(c, SHOP_SCHEMA, adapter);
    expect(r.passed).toBe(true);
    expect(calls).toBeGreaterThanOrEqual(1);
  });
});

describe('summarize + renderReport', () => {
  it('aggregates pass/fail counts and durations', () => {
    const s = summarize([
      { caseId: 'a', passed: true, reasons: [], durationMs: 5 },
      { caseId: 'b', passed: false, reasons: ['x'], durationMs: 7 },
      { caseId: 'c', passed: true, reasons: [], durationMs: 2 },
    ]);
    expect(s.total).toBe(3);
    expect(s.passed).toBe(2);
    expect(s.failed).toBe(1);
    expect(s.durationMs).toBe(14);
  });

  it('renderReport includes pass/fail markers and reasons', () => {
    const out = renderReport([
      { caseId: 'a', passed: true, reasons: [], durationMs: 1 },
      { caseId: 'b', passed: false, reasons: ['missing involved table: x'], durationMs: 2 },
    ]);
    expect(out).toContain('[PASS] a');
    expect(out).toContain('[FAIL] b');
    expect(out).toContain('missing involved table: x');
    expect(out).toContain('1/2 passed');
  });
});

describe('SHOP_EVAL_CASES has at least one case', () => {
  it('keeps the curated case list non-empty', () => {
    expect(SHOP_EVAL_CASES.length).toBeGreaterThan(0);
  });
});
