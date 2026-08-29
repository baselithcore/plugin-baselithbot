import { describe, expect, it } from 'vitest';
import { UnsafeSqlError } from '@dbview/shared';
import { SqlSafetyValidator, buildKnownSets } from './validator.js';
const graph = {
    kind: 'relational',
    dialect: 'postgres',
    generatedAt: new Date().toISOString(),
    edges: [],
    tables: [
        {
            id: 'public.customers',
            schema: 'public',
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
            id: 'public.orders',
            schema: 'public',
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
                {
                    name: 'amount',
                    dataType: 'numeric',
                    nullable: false,
                    isPrimaryKey: false,
                    isForeignKey: false,
                    isUnique: false,
                },
            ],
        },
    ],
};
const opts = () => ({
    dialect: 'postgres',
    allowDml: false,
    rowLimit: 100,
    ...buildKnownSets(graph),
});
describe('SqlSafetyValidator', () => {
    const v = new SqlSafetyValidator();
    it('rejects SELECT *', () => {
        expect(() => v.validate('SELECT * FROM customers', opts())).toThrow(UnsafeSqlError);
    });
    it('rejects DROP', () => {
        expect(() => v.validate('DROP TABLE customers', opts())).toThrow(UnsafeSqlError);
    });
    it('rejects DELETE without allowDml', () => {
        expect(() => v.validate('DELETE FROM customers', opts())).toThrow(UnsafeSqlError);
    });
    it('rejects multiple statements', () => {
        expect(() => v.validate('SELECT id FROM customers; SELECT id FROM orders', opts())).toThrow(UnsafeSqlError);
    });
    it('rejects unknown table', () => {
        expect(() => v.validate('SELECT id FROM nope', opts())).toThrow(UnsafeSqlError);
    });
    it('rejects unknown column on qualified reference', () => {
        expect(() => v.validate('SELECT customers.foo FROM customers LIMIT 5', opts())).toThrow(/Column 'customers\.foo' not in schema/);
    });
    it('rejects unknown column on aliased reference', () => {
        expect(() => v.validate('SELECT c.foo FROM customers c LIMIT 5', opts())).toThrow(/Column 'c\.foo' not in schema/);
    });
    it('rejects unknown bare column when single table is in scope', () => {
        expect(() => v.validate('SELECT foo FROM customers LIMIT 5', opts())).toThrow(/Column 'foo' not in schema/);
    });
    it('accepts SELECT-list output alias used in ORDER BY', () => {
        const r = v.validate('SELECT id AS pk, name FROM customers ORDER BY pk LIMIT 5', opts());
        expect(r.warnings.some((w) => w.severity === 'error')).toBe(false);
    });
    it('auto-rewrites wrong alias when column has a unique in-scope owner', () => {
        // `il.amount` would fail — `amount` is on `orders`, aliased `o` in the FROM.
        // Validator should rewrite `il.amount` → `o.amount` and emit an info warning.
        const r = v.validate('SELECT c.id, SUM(il.amount) AS total FROM customers c JOIN orders o ON o.customer_id = c.id GROUP BY c.id LIMIT 5', opts());
        expect(r.sql).toContain('o.amount');
        expect(r.sql).not.toContain('il.amount');
        expect(r.warnings.some((w) => w.code === 'unknown_column' && w.severity === 'info')).toBe(true);
    });
    it('still rejects when column is not in any in-scope table', () => {
        expect(() => v.validate('SELECT bogus_field FROM customers c LIMIT 5', opts())).toThrow(/Column 'bogus_field' not in schema/);
    });
    it('accepts dotted references inside aggregates and JOINs', () => {
        const r = v.validate('SELECT c.id, c.name, SUM(o.amount) AS total FROM customers c JOIN orders o ON o.customer_id = c.id GROUP BY c.id, c.name LIMIT 5', opts());
        expect(r.warnings.some((w) => w.severity === 'error')).toBe(false);
    });
    it('injects LIMIT when missing', () => {
        const r = v.validate('SELECT id, name FROM customers', opts());
        expect(r.sql.toUpperCase()).toContain('LIMIT 100');
        expect(r.warnings.some((w) => w.code === 'missing_limit')).toBe(true);
    });
    it('keeps existing LIMIT', () => {
        const r = v.validate('SELECT id, name FROM customers LIMIT 5', opts());
        expect(r.warnings.some((w) => w.code === 'missing_limit')).toBe(false);
    });
    it('accepts valid JOIN', () => {
        const r = v.validate('SELECT c.id, c.name, SUM(o.amount) AS total FROM customers c JOIN orders o ON o.customer_id = c.id GROUP BY c.id, c.name ORDER BY total DESC LIMIT 5', opts());
        expect(r.involvedTables.sort()).toEqual(['customers', 'orders']);
    });
    it('preserves original identifier case', () => {
        const r = v.validate('SELECT id, name FROM customers LIMIT 5', opts());
        expect(r.sql).toContain('customers');
        expect(r.sql).not.toContain('CUSTOMERS');
    });
    it('accepts CTE without flagging CTE name as unknown table', () => {
        const r = v.validate('WITH top_orders AS (SELECT customer_id, SUM(amount) AS total FROM orders GROUP BY customer_id) SELECT customer_id, total FROM top_orders LIMIT 10', opts());
        expect(r.involvedTables).toContain('orders');
        expect(r.involvedTables).not.toContain('top_orders');
    });
    it('rejects UPDATE without allowDml', () => {
        expect(() => v.validate("UPDATE customers SET name = 'x' WHERE id = 1", opts())).toThrow(UnsafeSqlError);
    });
    it('rejects ALTER', () => {
        expect(() => v.validate('ALTER TABLE customers ADD COLUMN x int', opts())).toThrow(UnsafeSqlError);
    });
    it('does not double-inject LIMIT into compound UNION queries that already end with LIMIT', () => {
        const r = v.validate("SELECT 'Customers' AS entity_type UNION ALL SELECT 'Orders' UNION ALL SELECT 'Order Items' LIMIT 100", opts());
        // Exactly one LIMIT clause must remain in the rewritten SQL.
        const matches = r.sql.match(/\bLIMIT\b/gi) ?? [];
        expect(matches.length).toBe(1);
        expect(r.warnings.some((w) => w.code === 'missing_limit')).toBe(false);
    });
    it('produces a concise parse error message (no pegjs token list)', () => {
        let caught = null;
        try {
            v.validate('SELECT . FROM customers', opts());
        }
        catch (err) {
            caught = err;
        }
        expect(caught).toBeInstanceOf(UnsafeSqlError);
        expect(caught.message).toMatch(/^SQL parse error: unexpected/);
        // The verbose pegjs "Expected ..." list must not leak into the user-facing message.
        expect(caught.message).not.toContain('Expected');
        expect(caught.message.length).toBeLessThan(300);
    });
});
//# sourceMappingURL=validator.test.js.map