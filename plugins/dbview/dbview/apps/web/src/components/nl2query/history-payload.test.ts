import { describe, expect, it } from 'vitest';
import type { Nl2SqlResponse } from '@dbview/shared';
import { HISTORY_WINDOW, buildHistoryPayload } from './history-payload.js';
import type { ChatTurn } from './turn-types.js';

function translation(query: string): Nl2SqlResponse {
  return {
    query,
    language: 'sql',
    dialect: 'postgres',
    explanation: '',
    joinNotes: [],
    involvedEntities: [],
    warnings: [],
    retries: 0,
    provider: 'ollama',
    model: 'codellama:7b',
  };
}

function ready(id: string, prompt: string, query: string, rowCount: number | undefined): ChatTurn {
  return {
    id,
    prompt,
    mode: 'ask',
    status: 'ready',
    translation: translation(query),
    result:
      rowCount === undefined
        ? undefined
        : { columns: ['id'], rows: [], rowCount, durationMs: 0, truncated: false },
    createdAt: 0,
  };
}

describe('buildHistoryPayload', () => {
  it('returns empty array for empty conversation', () => {
    expect(buildHistoryPayload([])).toEqual([]);
  });

  it('drops pending/error turns without a translation', () => {
    const conv: ChatTurn[] = [
      {
        id: 't1',
        prompt: 'pending one',
        mode: 'ask',
        status: 'translating',
        createdAt: 0,
      },
      {
        id: 't2',
        prompt: 'errored',
        mode: 'ask',
        status: 'error',
        error: 'boom',
        createdAt: 0,
      },
      ready('t3', 'top 5', 'SELECT id FROM shop.customers LIMIT 5', 5),
    ];
    const out = buildHistoryPayload(conv);
    expect(out).toHaveLength(1);
    expect(out[0]?.prompt).toBe('top 5');
  });

  it('caps at HISTORY_WINDOW most-recent turns', () => {
    const conv: ChatTurn[] = Array.from({ length: HISTORY_WINDOW + 3 }, (_, i) =>
      ready(`t${i}`, `q${i}`, `SELECT ${i} FROM t`, i),
    );
    const out = buildHistoryPayload(conv);
    expect(out).toHaveLength(HISTORY_WINDOW);
    expect(out[out.length - 1]?.prompt).toBe(`q${HISTORY_WINDOW + 2}`);
  });

  it('marks turns with execution errors as ok=false', () => {
    const turn = ready('t1', 'broken', 'SELECT bad FROM shop.customers', undefined);
    turn.executionError = { code: 'execution_failed', message: 'column does not exist' };
    const out = buildHistoryPayload([turn]);
    expect(out[0]?.ok).toBe(false);
  });

  it('serializes rowCount and language faithfully', () => {
    const out = buildHistoryPayload([ready('t1', 'how many', 'SELECT count(*) FROM t', 42)]);
    expect(out[0]).toEqual({
      prompt: 'how many',
      query: 'SELECT count(*) FROM t',
      language: 'sql',
      rowCount: 42,
      ok: true,
    });
  });
});
