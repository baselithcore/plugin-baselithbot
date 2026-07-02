import { describe, expect, it } from 'vitest';
import { buildRepairPrompt, isFixableSqlError } from './ask.service.js';

describe('isFixableSqlError', () => {
  it('repairs column-not-found errors', () => {
    expect(
      isFixableSqlError({ code: 'execution_failed', message: 'column "totl" does not exist' }),
    ).toBe(true);
  });

  it('repairs ambiguous-reference errors', () => {
    expect(
      isFixableSqlError({
        code: 'execution_failed',
        message: 'column reference "id" is ambiguous',
      }),
    ).toBe(true);
  });

  it('repairs syntax errors', () => {
    expect(
      isFixableSqlError({ code: 'execution_failed', message: 'syntax error at or near "FROOM"' }),
    ).toBe(true);
  });

  it('repairs Salesforce DataSource not-found errors', () => {
    expect(
      isFixableSqlError({
        code: 'execution_failed',
        message: 'DataSourceEntity not found: data_cloud.UnifiedThing__dlm',
      }),
    ).toBe(true);
  });

  it('skips connection refused', () => {
    expect(
      isFixableSqlError({ code: 'execution_failed', message: 'ECONNREFUSED 127.0.0.1:5432' }),
    ).toBe(false);
  });

  it('skips timeouts', () => {
    expect(isFixableSqlError({ code: 'execution_failed', message: 'query timed out' })).toBe(false);
  });

  it('skips auth/permission errors', () => {
    expect(
      isFixableSqlError({ code: 'execution_failed', message: 'permission denied for relation x' }),
    ).toBe(false);
    expect(isFixableSqlError({ code: 'unauthorized', message: 'invalid api key' })).toBe(false);
  });

  it('skips rate limits', () => {
    expect(isFixableSqlError({ code: 'execution_failed', message: 'rate limit exceeded' })).toBe(
      false,
    );
  });

  it('returns false on unrecognised opaque errors', () => {
    expect(isFixableSqlError({ code: 'execution_failed', message: 'something broke' })).toBe(false);
  });
});

describe('buildRepairPrompt', () => {
  it('embeds the original prompt, failed query and engine error', () => {
    const out = buildRepairPrompt(
      'top 5 accounts by total',
      'SELECT id, totl FROM accounts ORDER BY totl DESC LIMIT 5',
      'column "totl" does not exist',
    );
    expect(out).toContain('top 5 accounts by total');
    expect(out).toContain('SELECT id, totl FROM accounts');
    expect(out).toContain('column "totl" does not exist');
    expect(out).toContain('PRIOR ATTEMPT FAILED');
  });
});
