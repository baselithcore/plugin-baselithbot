import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { LlmGovernanceService } from './governance.service.js';

/**
 * Governance reads the enforcement decision straight from the child env vars
 * the host injects (`DBVIEW_LLM_ENFORCED_<SCOPE>`), so a fake credentials
 * service is enough — the only collaborator is BYOK resolution, which enforced
 * scopes must bypass.
 */
const PRINCIPAL: AuthPrincipal = {
  id: '11111111-1111-1111-1111-111111111111',
  email: 'u@test.local',
  role: 'user',
  source: 'jwt',
};

class FakeCredentials {
  resolveApiKey(): string | undefined {
    return 'sk-user-byok';
  }
}

function makeService(): LlmGovernanceService {
  return new LlmGovernanceService(new FakeCredentials() as never);
}

describe('LlmGovernanceService', () => {
  let prevNl2sql: string | undefined;
  let prevExplain: string | undefined;

  beforeEach(() => {
    prevNl2sql = process.env.DBVIEW_LLM_ENFORCED_NL2SQL;
    prevExplain = process.env.DBVIEW_LLM_ENFORCED_EXPLAIN;
    delete process.env.DBVIEW_LLM_ENFORCED_NL2SQL;
    delete process.env.DBVIEW_LLM_ENFORCED_EXPLAIN;
  });

  afterEach(() => {
    if (prevNl2sql === undefined) delete process.env.DBVIEW_LLM_ENFORCED_NL2SQL;
    else process.env.DBVIEW_LLM_ENFORCED_NL2SQL = prevNl2sql;
    if (prevExplain === undefined) delete process.env.DBVIEW_LLM_ENFORCED_EXPLAIN;
    else process.env.DBVIEW_LLM_ENFORCED_EXPLAIN = prevExplain;
  });

  it('reports no enforcement when the env vars are unset', () => {
    const state = makeService().state();
    expect(state.enforced).toBe(false);
    expect(state.translate).toEqual({ enforced: false, provider: null });
    expect(state.explain).toEqual({ enforced: false, provider: null });
  });

  it('reports per-scope enforcement from the injected env', () => {
    process.env.DBVIEW_LLM_ENFORCED_NL2SQL = 'openai';
    const state = makeService().state();
    expect(state.enforced).toBe(true);
    expect(state.translate).toEqual({ enforced: true, provider: 'openai' });
    expect(state.explain).toEqual({ enforced: false, provider: null });
  });

  it('ignores an invalid enforced provider value', () => {
    process.env.DBVIEW_LLM_ENFORCED_NL2SQL = 'not-a-provider';
    expect(makeService().state().translate.enforced).toBe(false);
  });

  it('unenforced translate keeps the requested provider and the BYOK key', () => {
    const r = makeService().resolveTranslate('openai', 'gpt-4o', 'sql', PRINCIPAL);
    expect(r.provider).toBe('openai');
    expect(r.model).toBe('gpt-4o');
    expect(r.auth.apiKey).toBe('sk-user-byok');
  });

  it('enforced translate overrides the requested provider/model and drops BYOK', () => {
    process.env.DBVIEW_LLM_ENFORCED_NL2SQL = 'anthropic';
    // Caller asks for openai/gpt-4o; the pin wins and BYOK is not consulted
    // (empty auth → the SDK reads the governed central key from env).
    const r = makeService().resolveTranslate('openai', 'gpt-4o', 'sql', PRINCIPAL);
    expect(r.provider).toBe('anthropic');
    expect(r.model).not.toBe('gpt-4o');
    expect(r.auth.apiKey).toBeUndefined();
  });

  it('enforced explain overrides provider and drops BYOK', () => {
    process.env.DBVIEW_LLM_ENFORCED_EXPLAIN = 'openai';
    const r = makeService().resolveExplain('ollama', PRINCIPAL);
    expect(r.provider).toBe('openai');
    expect(r.auth.apiKey).toBeUndefined();
  });
});
