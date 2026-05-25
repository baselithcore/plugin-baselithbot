import type { EvalCase } from '../types.js';

/**
 * Representative regression cases against the synthetic shop schema. Each
 * case encodes ONE behaviour the pipeline must keep across changes; if a
 * case starts failing after a refactor, the change has likely regressed
 * a real-world flow. Add cases here when fixing a production bug.
 */
export const SHOP_EVAL_CASES: EvalCase[] = [
  {
    id: 'top-customers-by-revenue',
    prompt: 'Top 5 customers by total revenue',
    expectations: {
      mustValidate: true,
      mustInvolveTables: ['shop.customers', 'shop.orders'],
      mustContain: ['order by', 'limit 5'],
      mustNotContain: ['select *'],
    },
  },
  {
    id: 'count-orders',
    prompt: 'How many orders are there?',
    expectations: {
      mustValidate: true,
      mustInvolveTables: ['shop.orders'],
      mustContain: ['count'],
    },
  },
  {
    id: 'list-products-vague',
    prompt: 'Show me some products',
    expectations: {
      mustValidate: true,
      mustInvolveTables: ['shop.products'],
      mustNotContain: ['select *', 'where'],
    },
  },
  {
    id: 'filter-by-status',
    prompt: 'List the 10 most recent orders with status "paid"',
    expectations: {
      mustValidate: true,
      mustInvolveTables: ['shop.orders'],
      mustContain: ['paid', 'limit 10'],
    },
  },
  {
    id: 'join-customer-order',
    prompt: 'For each customer, show their total order count and total spend',
    expectations: {
      mustValidate: true,
      mustInvolveTables: ['shop.customers', 'shop.orders'],
      mustContain: ['join', 'group by'],
    },
  },
  {
    id: 'top-by-nullable-metric',
    prompt: 'Top 5 products by price',
    expectations: {
      mustValidate: true,
      mustInvolveTables: ['shop.products'],
      // The sanitize layer must inject IS NOT NULL for top-N over nullable
      // metric columns — see grounding/sanitize.ts.
      mustContain: ['is not null', 'order by', 'limit 5'],
    },
  },
];
