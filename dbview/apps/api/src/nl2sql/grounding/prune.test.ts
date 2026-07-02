import { describe, expect, it } from 'vitest';
import type { Column, FKEdge, SchemaGraph, TableNode } from '@dbview/shared';
import { pruneRelationalSchema, tokenize } from './prune.js';

function col(name: string, extras: Partial<Column> = {}): Column {
  return {
    name,
    dataType: 'varchar',
    nullable: true,
    isPrimaryKey: false,
    isForeignKey: false,
    isUnique: false,
    ...extras,
  };
}

function table(id: string, columns: Column[], extras: Partial<TableNode> = {}): TableNode {
  const [schema, name] = id.includes('.') ? id.split('.') : ['public', id];
  return {
    id,
    schema: schema!,
    name: name!,
    columns,
    ...extras,
  };
}

function edge(source: string, target: string): FKEdge {
  return {
    id: `${source}->${target}`,
    source,
    sourceColumn: 'fk',
    target,
    targetColumn: 'id',
  };
}

function makeGraph(tables: TableNode[], edges: FKEdge[] = []): SchemaGraph {
  return {
    kind: 'relational',
    dialect: 'postgres',
    tables,
    edges,
    generatedAt: '2026-01-01T00:00:00.000Z',
  };
}

describe('tokenize', () => {
  it('lowercases, splits on non-word and drops short tokens', () => {
    expect(tokenize('Show TOP customers by Revenue')).toEqual(['customers', 'revenue']);
  });

  it('drops Italian stopwords', () => {
    expect(tokenize('mostra i primi 5 clienti per fatturato')).toEqual(['clienti', 'fatturato']);
  });

  it('dedupes', () => {
    expect(tokenize('Account Account Accounts')).toEqual(['account', 'accounts']);
  });
});

describe('pruneRelationalSchema', () => {
  const opts = { threshold: 5, maxTables: 8 };

  function bigSchema(): SchemaGraph {
    const tables = [
      table('s.accounts', [col('id', { isPrimaryKey: true }), col('name'), col('total')]),
      table('s.orders', [
        col('id', { isPrimaryKey: true }),
        col('account_id', { isForeignKey: true }),
        col('amount'),
      ]),
      table('s.customers', [col('id', { isPrimaryKey: true }), col('email')]),
      table('s.products', [col('id', { isPrimaryKey: true }), col('sku'), col('price')]),
      table('s.invoices', [
        col('id', { isPrimaryKey: true }),
        col('account_id', { isForeignKey: true }),
      ]),
      table('s.audit_log', [col('id'), col('action')]),
      table('s.settings', [col('key'), col('value')]),
      table('s.regions', [col('id'), col('name')]),
      table('s.shipments', [col('id'), col('order_id', { isForeignKey: true })]),
      table('s.refunds', [col('id'), col('order_id', { isForeignKey: true })]),
    ];
    const edges = [
      edge('s.orders', 's.accounts'),
      edge('s.invoices', 's.accounts'),
      edge('s.shipments', 's.orders'),
      edge('s.refunds', 's.orders'),
    ];
    return makeGraph(tables, edges);
  }

  it('returns input unchanged when below threshold', () => {
    const graph = makeGraph([table('s.a', [col('x')]), table('s.b', [col('y')])]);
    const r = pruneRelationalSchema(graph, 'show a', opts);
    expect(r.pruned).toBe(false);
    expect(r.graph).toBe(graph);
  });

  it('returns input unchanged when no token matches anything', () => {
    const graph = bigSchema();
    const r = pruneRelationalSchema(graph, 'gibberish wxyz', opts);
    expect(r.pruned).toBe(false);
    expect(r.graph.tables.length).toBe(graph.tables.length);
  });

  it('keeps the matching table and pulls 1-hop FK closure', () => {
    const r = pruneRelationalSchema(bigSchema(), 'top accounts by total', opts);
    expect(r.pruned).toBe(true);
    const ids = r.graph.tables.map((t) => t.id);
    expect(ids).toContain('s.accounts');
    // Closure: orders + invoices link directly to accounts.
    expect(ids).toContain('s.orders');
    expect(ids).toContain('s.invoices');
    // Audit / settings / products / regions are unrelated and must be dropped.
    expect(ids).not.toContain('s.audit_log');
    expect(ids).not.toContain('s.settings');
    expect(ids).not.toContain('s.products');
  });

  it('preserves only edges whose endpoints both survived pruning', () => {
    const r = pruneRelationalSchema(bigSchema(), 'top accounts by total', opts);
    for (const e of r.graph.edges) {
      const ids = new Set(r.graph.tables.map((t) => t.id));
      expect(ids.has(e.source)).toBe(true);
      expect(ids.has(e.target)).toBe(true);
    }
  });

  it('uses displayName tokens to ground entities with opaque technical names', () => {
    const tables = Array.from({ length: 10 }, (_, i) =>
      table(`s.t${i}`, [col('id')], { displayName: `Entity ${i}` })
    );
    tables.push(
      table('s.unifiedindividual__dlm', [col('Id__c')], {
        displayName: 'Unified Individual',
        description: 'Unified profile of a person across systems',
      })
    );
    const graph = makeGraph(tables);
    const r = pruneRelationalSchema(graph, 'count unified individuals', opts);
    expect(r.pruned).toBe(true);
    expect(r.graph.tables.map((t) => t.id)).toContain('s.unifiedindividual__dlm');
  });

  it('caps to maxTables even when closure would exceed it, keeping seeds', () => {
    const tables = [table('s.hub', [col('id'), col('hub_name')])];
    for (let i = 0; i < 20; i += 1) {
      tables.push(table(`s.spoke${i}`, [col('id'), col('hub_id', { isForeignKey: true })]));
    }
    const edges = Array.from({ length: 20 }, (_, i) => edge(`s.spoke${i}`, 's.hub'));
    const graph = makeGraph(tables, edges);
    const r = pruneRelationalSchema(graph, 'show hub', { threshold: 5, maxTables: 5 });
    expect(r.pruned).toBe(true);
    expect(r.graph.tables.length).toBeLessThanOrEqual(5);
    expect(r.graph.tables.map((t) => t.id)).toContain('s.hub');
  });
});
