import type { ExecuteQueryResponse } from '@dbview/shared';
import type { SalesforceClient, SalesforceQueryRow } from './client.js';

/**
 * Salesforce SOQL executor. The caller is expected to pass an already-validated
 * SOQL query (see SalesforceSafetyValidator). This module only performs
 * execution + result projection, no extra safety enforcement.
 */
export class SalesforceExecutor {
  constructor(private readonly client: SalesforceClient) {}

  async run(soql: string, rowLimit: number): Promise<ExecuteQueryResponse> {
    const start = Date.now();
    const records = await this.client.query(soql, rowLimit);
    const durationMs = Date.now() - start;
    const { columns, rows } = projectRecords(records);
    return {
      columns,
      rows,
      rowCount: rows.length,
      durationMs,
      truncated: rows.length >= rowLimit,
    };
  }

  async close(): Promise<void> {
    await this.client.close();
  }
}

/**
 * Flatten Salesforce records to (columns, rows). The set of columns is the
 * union of top-level keys observed across records (excluding the `attributes`
 * metadata envelope). Nested objects (parent lookups via dot-notation in SOQL)
 * are serialized as JSON strings to keep the table view single-cell-friendly.
 */
function projectRecords(records: SalesforceQueryRow[]): {
  columns: string[];
  rows: unknown[][];
} {
  const colSet: string[] = [];
  const seen = new Set<string>();
  for (const r of records) {
    for (const k of Object.keys(r)) {
      if (k === 'attributes') continue;
      if (!seen.has(k)) {
        seen.add(k);
        colSet.push(k);
      }
    }
  }
  const rows = records.map((r) =>
    colSet.map((c) => {
      const v = r[c];
      if (v && typeof v === 'object') {
        const stripped = stripAttributes(v as Record<string, unknown>);
        return JSON.stringify(stripped);
      }
      return v ?? null;
    })
  );
  return { columns: colSet, rows };
}

function stripAttributes(obj: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj)) {
    if (k === 'attributes') continue;
    out[k] = v;
  }
  return out;
}
