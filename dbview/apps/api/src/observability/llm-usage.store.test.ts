import { describe, expect, it } from 'vitest';
import {
  recordLlmUsage,
  serializeUsage,
  withUsageCapture,
  type UsageRow,
} from './llm-usage.store.js';

describe('llm usage store', () => {
  it('accumulates usage recorded inside a request scope', () => {
    const rows: UsageRow[] = [];
    withUsageCapture(rows, () => {
      recordLlmUsage('codellama:7b', { promptTokens: 1200, completionTokens: 80 });
      recordLlmUsage('codellama:7b', { promptTokens: 30, completionTokens: 5 });
    });
    expect(rows).toHaveLength(2);
    expect(serializeUsage(rows)).toBe('codellama:7b;1200;80,codellama:7b;30;5');
  });

  it('ignores usage recorded outside a request scope', () => {
    // Engine startup / background work has no request to bill — it must not
    // throw, and must not leak into the next request's header either.
    expect(() => recordLlmUsage('m', { promptTokens: 5, completionTokens: 5 })).not.toThrow();
  });

  it('drops a provider that reported nothing', () => {
    const rows: UsageRow[] = [];
    withUsageCapture(rows, () => {
      recordLlmUsage('m', undefined);
      recordLlmUsage('m', { promptTokens: 0, completionTokens: 0 });
    });
    expect(rows).toEqual([]);
    expect(serializeUsage(rows)).toBe('');
  });

  it('keeps each request isolated', () => {
    const first: UsageRow[] = [];
    const second: UsageRow[] = [];
    withUsageCapture(first, () => recordLlmUsage('a', { promptTokens: 1, completionTokens: 1 }));
    withUsageCapture(second, () => recordLlmUsage('b', { promptTokens: 2, completionTokens: 2 }));
    expect(serializeUsage(first)).toBe('a;1;1');
    expect(serializeUsage(second)).toBe('b;2;2');
  });

  it('sanitizes a model id that would corrupt the header', () => {
    const rows: UsageRow[] = [];
    withUsageCapture(rows, () =>
      recordLlmUsage('evil;model,name\r\n', { promptTokens: 3, completionTokens: 4 })
    );
    expect(serializeUsage(rows)).toBe('evilmodelname;3;4');
  });
});
