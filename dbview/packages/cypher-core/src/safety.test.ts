import { describe, expect, it } from 'vitest';
import { UnsafeSqlError, type PropertyGraphSchema } from '@dbview/shared';
import { CypherSafetyValidator } from './safety.js';

const schema: PropertyGraphSchema = {
  kind: 'graph',
  dialect: 'neo4j',
  generatedAt: new Date().toISOString(),
  labels: [
    {
      id: 'Customer',
      label: 'Customer',
      properties: [
        { name: 'id', types: ['INTEGER'], nullable: false },
        { name: 'name', types: ['STRING'], nullable: true },
      ],
    },
    {
      id: 'Order',
      label: 'Order',
      properties: [
        { name: 'id', types: ['INTEGER'], nullable: false },
        { name: 'status', types: ['STRING'], nullable: true, sampleValues: ['paid', 'pending'] },
        { name: 'total', types: ['FLOAT'], nullable: true },
      ],
    },
  ],
  relationships: [
    {
      id: 'r1',
      type: 'PLACED',
      source: 'Customer',
      target: 'Order',
      properties: [],
    },
  ],
};

const opts = (overrides: Partial<{ rowLimit: number; allowWrites: boolean }> = {}) => ({
  schema,
  rowLimit: 100,
  allowWrites: false,
  ...overrides,
});

describe('CypherSafetyValidator', () => {
  const v = new CypherSafetyValidator();

  it('accepts valid MATCH', () => {
    const r = v.validate(
      'MATCH (c:Customer)-[:PLACED]->(o:Order) RETURN c.id, o.id LIMIT 10',
      opts(),
    );
    expect(r.involvedLabels.sort()).toEqual(['Customer', 'Order']);
  });

  it('rejects CREATE', () => {
    expect(() => v.validate('CREATE (n:Customer) RETURN n', opts())).toThrow(UnsafeSqlError);
  });

  it('rejects DELETE', () => {
    expect(() => v.validate('MATCH (n) DELETE n', opts())).toThrow(UnsafeSqlError);
  });

  it('rejects DETACH DELETE', () => {
    expect(() => v.validate('MATCH (n:Customer) DETACH DELETE n', opts())).toThrow(UnsafeSqlError);
  });

  it('rejects MERGE', () => {
    expect(() => v.validate('MERGE (c:Customer {id:1})', opts())).toThrow(UnsafeSqlError);
  });

  it('rejects SET', () => {
    expect(() => v.validate('MATCH (n:Customer) SET n.name = "x"', opts())).toThrow(UnsafeSqlError);
  });

  it('rejects unknown label', () => {
    expect(() => v.validate('MATCH (n:Foo) RETURN n', opts())).toThrow(UnsafeSqlError);
  });

  it('rejects multiple statements', () => {
    expect(() =>
      v.validate('MATCH (n:Customer) RETURN n; MATCH (o:Order) RETURN o', opts()),
    ).toThrow(UnsafeSqlError);
  });

  it('rejects dangerous procs', () => {
    expect(() =>
      v.validate('CALL apoc.create.node(["Customer"], {}) YIELD node RETURN node', opts()),
    ).toThrow(UnsafeSqlError);
  });

  it('auto-injects LIMIT', () => {
    const r = v.validate('MATCH (c:Customer) RETURN c.id', opts());
    expect(r.query).toMatch(/LIMIT 100$/);
    expect(r.warnings.some((w) => w.code === 'missing_limit')).toBe(true);
  });

  it('rejects trailing WITH (no RETURN)', () => {
    expect(() =>
      v.validate(
        'MATCH (c:Customer)-[:PLACED]->(o:Order) WITH c, SUM(o.total) AS total ORDER BY total DESC LIMIT 5',
        opts(),
      ),
    ).toThrow(UnsafeSqlError);
  });

  it('rejects schema type leak in property map', () => {
    expect(() =>
      v.validate('MATCH (c:Customer)-[:PLACED {qty: INTEGER}]->(o:Order) RETURN c LIMIT 5', opts()),
    ).toThrow(UnsafeSqlError);
  });

  it('rejects invented property reference', () => {
    expect(() =>
      v.validate(
        'MATCH (c:Customer)-[:PLACED]->(o:Order) WHERE o.createdAt > 0 RETURN c LIMIT 5',
        opts(),
      ),
    ).toThrow(UnsafeSqlError);
  });
});
