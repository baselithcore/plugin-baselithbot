import { describe, expect, it } from 'vitest';
import { SalesforceDataCloudExecutor } from './executor.js';
import type { SalesforceDataCloudClient, SdcQueryPage } from './client.js';

function makeClient(pages: SdcQueryPage[]): SalesforceDataCloudClient {
  let i = 0;
  return {
    async query() {
      return pages[i++]!;
    },
    async nextPage() {
      return pages[i++]!;
    },
    async close() {},
  } as unknown as SalesforceDataCloudClient;
}

describe('SalesforceDataCloudExecutor', () => {
  it('returns rows in column order derived from metadata.placeInOrder', async () => {
    const page: SdcQueryPage = {
      data: [
        { Name: 'A', Id: '1' },
        { Name: 'B', Id: '2' },
      ],
      metadata: {
        Name: { type: 'STRING_TYPE', placeInOrder: 1 },
        Id: { type: 'STRING_TYPE', placeInOrder: 0 },
      },
      done: true,
    };
    const exec = new SalesforceDataCloudExecutor(makeClient([page]));
    const r = await exec.run('SELECT Id, Name FROM X__dlm LIMIT 10', 10);
    expect(r.columns).toEqual(['Id', 'Name']);
    expect(r.rows).toEqual([
      ['1', 'A'],
      ['2', 'B'],
    ]);
    expect(r.rowCount).toBe(2);
    expect(r.truncated).toBe(false);
  });

  it('paginates with nextBatchId until done', async () => {
    const pages: SdcQueryPage[] = [
      {
        data: [{ Id: '1' }],
        metadata: { Id: { type: 'STRING_TYPE', placeInOrder: 0 } },
        done: false,
        nextBatchId: 'batch1',
      },
      {
        data: [{ Id: '2' }],
        metadata: { Id: { type: 'STRING_TYPE', placeInOrder: 0 } },
        done: false,
        nextBatchId: 'batch2',
      },
      {
        data: [{ Id: '3' }],
        metadata: { Id: { type: 'STRING_TYPE', placeInOrder: 0 } },
        done: true,
      },
    ];
    const r = await new SalesforceDataCloudExecutor(makeClient(pages)).run('q', 100);
    expect(r.rows).toEqual([['1'], ['2'], ['3']]);
    expect(r.truncated).toBe(false);
  });

  it('stops once rowLimit is reached and marks truncated', async () => {
    const pages: SdcQueryPage[] = [
      {
        data: [{ Id: '1' }, { Id: '2' }, { Id: '3' }],
        metadata: { Id: { type: 'STRING_TYPE', placeInOrder: 0 } },
        done: false,
        nextBatchId: 'b',
      },
    ];
    const r = await new SalesforceDataCloudExecutor(makeClient(pages)).run('q', 2);
    expect(r.rows).toEqual([['1'], ['2']]);
    expect(r.truncated).toBe(true);
  });

  it('falls back to first-row keys when metadata is missing', async () => {
    const page: SdcQueryPage = {
      data: [{ A: 1, B: 2 }],
      done: true,
    };
    const r = await new SalesforceDataCloudExecutor(makeClient([page])).run('q', 10);
    expect(r.columns).toEqual(['A', 'B']);
    expect(r.rows).toEqual([[1, 2]]);
  });

  it('normalizes missing cells to null', async () => {
    const page: SdcQueryPage = {
      data: [{ A: 1 }],
      metadata: {
        A: { type: 'NUMBER_TYPE', placeInOrder: 0 },
        B: { type: 'STRING_TYPE', placeInOrder: 1 },
      },
      done: true,
    };
    const r = await new SalesforceDataCloudExecutor(makeClient([page])).run('q', 10);
    expect(r.rows).toEqual([[1, null]]);
  });

  it('handles positional-array rows (v2 Connect API default shape)', async () => {
    const page: SdcQueryPage = {
      data: [
        ['1', 'Alice', 100],
        ['2', 'Bob', 200],
      ],
      metadata: {
        Id: { type: 'STRING_TYPE', placeInOrder: 0 },
        Name: { type: 'STRING_TYPE', placeInOrder: 1 },
        Score: { type: 'NUMBER_TYPE', placeInOrder: 2 },
      },
      done: true,
    };
    const r = await new SalesforceDataCloudExecutor(makeClient([page])).run('q', 10);
    expect(r.columns).toEqual(['Id', 'Name', 'Score']);
    expect(r.rows).toEqual([
      ['1', 'Alice', 100],
      ['2', 'Bob', 200],
    ]);
  });

  it('respects placeInOrder when reordering positional cells', async () => {
    const page: SdcQueryPage = {
      // wire order: Score, Id, Name
      data: [[42, 'X', 'Zed']],
      metadata: {
        Id: { type: 'STRING_TYPE', placeInOrder: 1 },
        Name: { type: 'STRING_TYPE', placeInOrder: 2 },
        Score: { type: 'NUMBER_TYPE', placeInOrder: 0 },
      },
      done: true,
    };
    const r = await new SalesforceDataCloudExecutor(makeClient([page])).run('q', 10);
    expect(r.columns).toEqual(['Score', 'Id', 'Name']);
    expect(r.rows).toEqual([[42, 'X', 'Zed']]);
  });
});
