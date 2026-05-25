import type { ExecuteQueryResponse } from '@dbview/shared';
import type { SalesforceDataCloudClient, SdcQueryPage } from './client.js';

/**
 * Salesforce Data Cloud query executor.
 *
 * `/api/v2/query` response shape (current Connect API):
 *   {
 *     data:     unknown[][],                          // positional row arrays
 *     metadata: { [col]: { type, placeInOrder, ... }} // col → array index
 *     done:     boolean,
 *     nextBatchId?: string,
 *     rowCount?: number,
 *     ...
 *   }
 *
 * Legacy v1 endpoints — and a handful of edge cases on v2 — emit rows as
 * objects keyed by column name. We handle both shapes by detecting whether
 * the first row is an Array (positional) or an Object (keyed).
 *
 * Pagination: when `done=false`, the server returns `nextBatchId`. We loop
 * through `nextPage()` until `done` or `rowLimit` is reached.
 */
export class SalesforceDataCloudExecutor {
  constructor(private readonly client: SalesforceDataCloudClient) {}

  async run(sql: string, rowLimit: number): Promise<ExecuteQueryResponse> {
    const start = Date.now();
    let page = await this.client.query(sql);
    const columns = resolveColumns(page);
    const positions = resolvePositions(page, columns);
    const rows: unknown[][] = [];
    appendRows(rows, page, columns, positions, rowLimit);

    while (rows.length < rowLimit && page.done === false && page.nextBatchId) {
      page = await this.client.nextPage(page.nextBatchId);
      appendRows(rows, page, columns, positions, rowLimit);
    }

    const truncated = rows.length >= rowLimit && (page.done === false || rows.length === rowLimit);
    return {
      columns,
      rows,
      rowCount: rows.length,
      durationMs: Date.now() - start,
      truncated,
    };
  }

  async close(): Promise<void> {
    await this.client.close();
  }
}

/**
 * Determine output column names in projection order.
 *
 * Preference order:
 *  1. `metadata` keys sorted by `placeInOrder`.
 *  2. First row's keys (only meaningful for legacy keyed-row responses).
 *  3. `col0..colN` synthetic names if the row is positional and metadata is
 *     missing — defensive fallback so the UI still renders something.
 */
function resolveColumns(page: SdcQueryPage): string[] {
  if (page.metadata && Object.keys(page.metadata).length > 0) {
    const entries = Object.entries(page.metadata);
    entries.sort((a, b) => {
      const ao = a[1].placeInOrder ?? Number.MAX_SAFE_INTEGER;
      const bo = b[1].placeInOrder ?? Number.MAX_SAFE_INTEGER;
      return ao - bo;
    });
    return entries.map(([k]) => k);
  }
  const first = page.data?.[0];
  if (Array.isArray(first)) {
    return first.map((_, i) => `col${i}`);
  }
  return first ? Object.keys(first as Record<string, unknown>) : [];
}

/**
 * Pre-compute positional index for each output column. Used when the page
 * emits positional rows. Falls back to columns natural order (0..N) when
 * `metadata.placeInOrder` is missing.
 */
function resolvePositions(page: SdcQueryPage, columns: string[]): number[] {
  if (page.metadata) {
    return columns.map((c, i) => page.metadata?.[c]?.placeInOrder ?? i);
  }
  return columns.map((_, i) => i);
}

function appendRows(
  out: unknown[][],
  page: SdcQueryPage,
  columns: string[],
  positions: number[],
  rowLimit: number
): void {
  for (const row of page.data ?? []) {
    if (out.length >= rowLimit) return;
    if (Array.isArray(row)) {
      out.push(positions.map((p) => normalizeCell(row[p])));
    } else {
      const obj = row as Record<string, unknown>;
      out.push(columns.map((c) => normalizeCell(obj[c])));
    }
  }
}

function normalizeCell(v: unknown): unknown {
  if (v === undefined) return null;
  return v;
}
