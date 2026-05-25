import { describe, expect, it } from 'vitest';
import { UnsafeSqlError, type SchemaGraph } from '@dbview/shared';
import { SqlSafetyValidator, buildKnownSets } from './validator.js';

/**
 * Golden cases mirror real-world LLM-generated SQL. Each entry pins a
 * representative shape (CTE, subquery, window, quoted ident, etc.) that
 * has historically tripped the validator or its parser.
 *
 * Cases live in one file so regressions show up as a diff against this
 * snapshot rather than scattered failures.
 */

const graph: SchemaGraph = {
  kind: 'relational',
  dialect: 'postgres',
  generatedAt: new Date().toISOString(),
  edges: [],
  tables: [
    {
      id: 'public.users',
      schema: 'public',
      name: 'users',
      columns: [
        col('id', 'integer', { isPrimaryKey: true }),
        col('email', 'text'),
        col('created_at', 'timestamptz'),
      ],
    },
    {
      id: 'public.orders',
      schema: 'public',
      name: 'orders',
      columns: [
        col('id', 'integer', { isPrimaryKey: true }),
        col('user_id', 'integer', { isForeignKey: true }),
        col('total', 'numeric'),
        col('created_at', 'timestamptz'),
      ],
    },
    {
      id: 'public.Order_Items',
      schema: 'public',
      name: 'Order_Items',
      columns: [
        col('order_id', 'integer', { isForeignKey: true }),
        col('product_id', 'integer'),
        col('qty', 'integer'),
        col('price', 'numeric'),
      ],
    },
  ],
};

function col(
  name: string,
  dataType: string,
  flags: Partial<{ isPrimaryKey: boolean; isForeignKey: boolean; isUnique: boolean }> = {},
) {
  return {
    name,
    dataType,
    nullable: true,
    isPrimaryKey: !!flags.isPrimaryKey,
    isForeignKey: !!flags.isForeignKey,
    isUnique: !!flags.isUnique,
  };
}

const opts = () => ({
  dialect: 'postgres' as const,
  allowDml: false,
  rowLimit: 50,
  ...buildKnownSets(graph),
});

describe('SqlSafetyValidator — golden patterns', () => {
  const v = new SqlSafetyValidator();

  describe('DDL & admin (must reject)', () => {
    const forbidden: Array<[string, string]> = [
      ['CREATE INDEX', 'CREATE INDEX idx_users_email ON users(email)'],
      ['TRUNCATE', 'TRUNCATE TABLE orders'],
      ['GRANT', 'GRANT SELECT ON users TO public'],
      ['REVOKE', 'REVOKE SELECT ON users FROM public'],
      ['SET', 'SET search_path TO public'],
    ];
    for (const [label, sql] of forbidden) {
      it(`rejects ${label}`, () => {
        expect(() => v.validate(sql, opts())).toThrow(UnsafeSqlError);
      });
    }
  });

  describe('DML default-blocked', () => {
    const dml: Array<[string, string]> = [
      ['INSERT', "INSERT INTO users(email) VALUES ('a@b')"],
      ['UPDATE', "UPDATE users SET email = 'x' WHERE id = 1"],
      ['DELETE', 'DELETE FROM orders WHERE id = 1'],
    ];
    for (const [label, sql] of dml) {
      it(`blocks ${label} when allowDml=false`, () => {
        expect(() => v.validate(sql, opts())).toThrow(UnsafeSqlError);
      });
    }
  });

  describe('SELECT shapes accepted', () => {
    it('quoted mixed-case identifier preserved', () => {
      const r = v.validate('SELECT order_id, qty FROM "Order_Items" LIMIT 5', opts());
      expect(r.sql).toContain('"Order_Items"');
      expect(r.involvedTables).toContain('Order_Items');
    });

    it('subquery in FROM', () => {
      const r = v.validate('SELECT u.email FROM (SELECT id, email FROM users) u LIMIT 10', opts());
      expect(r.involvedTables).toContain('users');
    });

    it('window function', () => {
      const r = v.validate(
        'SELECT id, total, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY total DESC) AS rn FROM orders LIMIT 25',
        opts(),
      );
      expect(r.warnings.some((w) => w.code === 'missing_limit')).toBe(false);
    });

    it('chained CTEs do not leak into unknown table errors', () => {
      const sql =
        'WITH t1 AS (SELECT id FROM users), t2 AS (SELECT id FROM t1) SELECT id FROM t2 LIMIT 5';
      const r = v.validate(sql, opts());
      expect(r.involvedTables).toContain('users');
      expect(r.involvedTables).not.toContain('t1');
      expect(r.involvedTables).not.toContain('t2');
    });

    it('inner unknown table inside subquery still fails', () => {
      expect(() => v.validate('SELECT id FROM (SELECT id FROM nope) sub LIMIT 5', opts())).toThrow(
        UnsafeSqlError,
      );
    });
  });

  describe('LIMIT injection edges', () => {
    it('injects limit when missing on bare SELECT', () => {
      const r = v.validate('SELECT id FROM users', opts());
      expect(r.sql.toUpperCase()).toMatch(/LIMIT 50\b/);
    });

    it('does not inject when LIMIT already at outer level', () => {
      const r = v.validate('SELECT id FROM users LIMIT 3', opts());
      const matches = r.sql.match(/\bLIMIT\b/gi) ?? [];
      expect(matches.length).toBe(1);
    });

    it('counts UNION outer LIMIT only', () => {
      const r = v.validate('SELECT id FROM users UNION ALL SELECT id FROM orders LIMIT 7', opts());
      const matches = r.sql.match(/\bLIMIT\b/gi) ?? [];
      expect(matches.length).toBe(1);
    });
  });

  describe('star rejection', () => {
    it('rejects SELECT *', () => {
      expect(() => v.validate('SELECT * FROM users LIMIT 5', opts())).toThrow(UnsafeSqlError);
    });

    it('rejects SELECT t.*', () => {
      expect(() => v.validate('SELECT u.* FROM users u LIMIT 5', opts())).toThrow(UnsafeSqlError);
    });
  });

  describe('separator/multi-statement guard', () => {
    it('strips trailing semicolon but parses single statement', () => {
      const r = v.validate('SELECT id FROM users LIMIT 5;', opts());
      expect(r.sql).not.toMatch(/;\s*$/);
    });

    it('rejects two statements joined by semicolon', () => {
      expect(() =>
        v.validate('SELECT id FROM users LIMIT 1; SELECT id FROM orders LIMIT 1', opts()),
      ).toThrow(UnsafeSqlError);
    });
  });
});
