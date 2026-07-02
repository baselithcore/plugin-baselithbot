import type { Column, FKEdge, SchemaGraph, TableNode } from '@dbview/shared';
import { SalesforceClient } from './client.js';

interface SObjectListItem {
  name: string;
  label?: string;
  queryable: boolean;
  custom: boolean;
  deprecatedAndHidden?: boolean;
}

interface SObjectListResponse {
  sobjects: SObjectListItem[];
}

interface SObjectFieldDescribe {
  name: string;
  type: string;
  nillable: boolean;
  unique?: boolean;
  defaultValue?: unknown;
  // Reference fields list the target sObjects (e.g. Lookup → Account = ["Account"]).
  referenceTo?: string[];
  relationshipName?: string | null;
}

interface SObjectDescribeResponse {
  name: string;
  fields: SObjectFieldDescribe[];
}

/**
 * Salesforce schema introspector.
 *
 * Strategy:
 *  - List sObjects via `/services/data/<v>/sobjects`. Filter: queryable && !deprecated.
 *    Skip system feed/share/history junk to keep the graph readable.
 *  - Describe each kept sObject in parallel (bounded concurrency) to gather fields + lookups.
 *  - Build relational SchemaGraph: sObject → TableNode, reference field → FKEdge.
 */
export class SalesforceIntrospector {
  private readonly client: SalesforceClient;
  private readonly apiVersion: string;

  constructor(client: SalesforceClient, apiVersion: string) {
    this.client = client;
    this.apiVersion = apiVersion;
  }

  async introspect(): Promise<SchemaGraph> {
    const list = await this.client.get<SObjectListResponse>(
      `/services/data/${this.apiVersion}/sobjects`
    );
    const targets = list.sobjects.filter((s) => isInterestingSObject(s));
    const describes = await runWithConcurrency(targets, 8, (s) =>
      this.client.get<SObjectDescribeResponse>(
        `/services/data/${this.apiVersion}/sobjects/${encodeURIComponent(s.name)}/describe`
      )
    );

    const known = new Set(targets.map((s) => s.name));
    const tables: TableNode[] = describes.map((d) => describeToTable(d));
    const edges: FKEdge[] = [];
    for (const d of describes) {
      for (const f of d.fields) {
        if (!f.referenceTo) continue;
        for (const target of f.referenceTo) {
          if (!known.has(target)) continue;
          edges.push({
            id: `${d.name}.${f.name}->${target}.Id`,
            source: `salesforce.${d.name}`,
            sourceColumn: f.name,
            target: `salesforce.${target}`,
            targetColumn: 'Id',
            constraintName: f.relationshipName ?? undefined,
          });
        }
      }
    }

    return {
      kind: 'relational',
      dialect: 'salesforce',
      tables,
      edges,
      generatedAt: new Date().toISOString(),
    };
  }

  async close(): Promise<void> {
    await this.client.close();
  }
}

function describeToTable(d: SObjectDescribeResponse): TableNode {
  const refSet = new Set(
    d.fields.filter((f) => f.referenceTo && f.referenceTo.length).map((f) => f.name)
  );
  const columns: Column[] = d.fields.map((f) => ({
    name: f.name,
    dataType: f.type,
    nullable: f.nillable,
    isPrimaryKey: f.name === 'Id',
    isForeignKey: refSet.has(f.name),
    isUnique: f.unique ?? false,
    defaultValue: f.defaultValue == null ? null : String(f.defaultValue),
  }));
  return {
    id: `salesforce.${d.name}`,
    schema: 'salesforce',
    name: d.name,
    columns,
  };
}

function isInterestingSObject(s: SObjectListItem): boolean {
  if (!s.queryable) return false;
  if (s.deprecatedAndHidden) return false;
  // Drop high-volume system/audit sObjects that bloat the graph without value.
  return !/(History|Feed|Share|ChangeEvent|Tag|Vote|Subscription|StreamingChannel)$/.test(s.name);
}

async function runWithConcurrency<T, R>(
  items: T[],
  concurrency: number,
  fn: (item: T) => Promise<R>
): Promise<R[]> {
  const out: R[] = new Array(items.length);
  let next = 0;
  const workers = Array.from({ length: Math.min(concurrency, items.length) }, async () => {
    while (true) {
      const i = next++;
      if (i >= items.length) return;
      const item = items[i] as T;
      out[i] = await fn(item);
    }
  });
  await Promise.all(workers);
  return out;
}
