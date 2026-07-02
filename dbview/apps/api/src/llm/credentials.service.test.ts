import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { LlmCredentialsStore } from './credentials.store.js';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { LlmCredentialsService } from './credentials.service.js';

const PRINCIPAL: AuthPrincipal = {
  id: '11111111-1111-1111-1111-111111111111',
  email: 'u@test.local',
  role: 'user',
  source: 'jwt',
};

const OTHER: AuthPrincipal = {
  ...PRINCIPAL,
  id: '22222222-2222-2222-2222-222222222222',
};

describe('LlmCredentialsService', () => {
  let dir: string;
  let prevDataDir: string | undefined;
  let prevSecret: string | undefined;
  let prevOpenai: string | undefined;
  let prevAnthropic: string | undefined;

  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), 'dbview-creds-'));
    prevDataDir = process.env.DBVIEW_DATA_DIR;
    prevSecret = process.env.DBVIEW_SECRET;
    prevOpenai = process.env.OPENAI_API_KEY;
    prevAnthropic = process.env.ANTHROPIC_API_KEY;
    process.env.DBVIEW_DATA_DIR = dir;
    process.env.DBVIEW_SECRET = 'test-secret-1234567890abcdef';
    delete process.env.OPENAI_API_KEY;
    delete process.env.ANTHROPIC_API_KEY;
  });

  afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
    restore('DBVIEW_DATA_DIR', prevDataDir);
    restore('DBVIEW_SECRET', prevSecret);
    restore('OPENAI_API_KEY', prevOpenai);
    restore('ANTHROPIC_API_KEY', prevAnthropic);
  });

  it('reports no key when nothing stored and no env fallback', () => {
    const svc = new LlmCredentialsService();
    const status = svc.status('openai', PRINCIPAL);
    expect(status).toMatchObject({ provider: 'openai', hasKey: false, envFallback: false });
  });

  it('stores, decrypts, and removes per-user keys', () => {
    const svc = new LlmCredentialsService();
    svc.upsert('openai', 'sk-test-1234567890', PRINCIPAL);
    expect(svc.resolveApiKey('openai', PRINCIPAL)).toBe('sk-test-1234567890');
    const status = svc.status('openai', PRINCIPAL);
    expect(status.hasKey).toBe(true);
    expect(status.envFallback).toBe(false);
    expect(status.maskedTail).toBe('••••7890');

    svc.remove('openai', PRINCIPAL);
    expect(svc.resolveApiKey('openai', PRINCIPAL)).toBeUndefined();
    expect(svc.status('openai', PRINCIPAL).hasKey).toBe(false);
  });

  it('isolates keys per user', () => {
    const svc = new LlmCredentialsService();
    svc.upsert('openai', 'sk-user-aaaa1234', PRINCIPAL);
    svc.upsert('openai', 'sk-user-bbbb5678', OTHER);
    expect(svc.resolveApiKey('openai', PRINCIPAL)).toBe('sk-user-aaaa1234');
    expect(svc.resolveApiKey('openai', OTHER)).toBe('sk-user-bbbb5678');
  });

  it('isolates keys per provider', () => {
    const svc = new LlmCredentialsService();
    svc.upsert('openai', 'sk-open-12345678', PRINCIPAL);
    svc.upsert('anthropic', 'sk-ant-87654321', PRINCIPAL);
    expect(svc.resolveApiKey('openai', PRINCIPAL)).toBe('sk-open-12345678');
    expect(svc.resolveApiKey('anthropic', PRINCIPAL)).toBe('sk-ant-87654321');
  });

  it('falls back to env when no stored key', () => {
    process.env.OPENAI_API_KEY = 'env-openai-key-xxxx';
    const svc = new LlmCredentialsService();
    expect(svc.resolveApiKey('openai', PRINCIPAL)).toBe('env-openai-key-xxxx');
    expect(svc.status('openai', PRINCIPAL)).toMatchObject({
      hasKey: true,
      envFallback: true,
      maskedTail: '••••xxxx',
    });
  });

  it('prefers stored over env when both present', () => {
    process.env.OPENAI_API_KEY = 'env-openai-fallback';
    const svc = new LlmCredentialsService();
    svc.upsert('openai', 'sk-user-stored123', PRINCIPAL);
    expect(svc.resolveApiKey('openai', PRINCIPAL)).toBe('sk-user-stored123');
    expect(svc.status('openai', PRINCIPAL).envFallback).toBe(false);
  });

  it('persists across instances', () => {
    const svc = new LlmCredentialsService();
    svc.upsert('anthropic', 'sk-ant-persist1234', PRINCIPAL);

    const svc2 = new LlmCredentialsService();
    expect(svc2.resolveApiKey('anthropic', PRINCIPAL)).toBe('sk-ant-persist1234');
  });

  it('persistence uses an atomic write (mode 0600)', () => {
    const svc = new LlmCredentialsService();
    svc.upsert('openai', 'sk-test-9999', PRINCIPAL);
    const store = new LlmCredentialsStore();
    expect(store.get(PRINCIPAL.id, 'openai')).toBeDefined();
  });
});

function restore(name: string, prev: string | undefined): void {
  if (prev === undefined) delete process.env[name];
  else process.env[name] = prev;
}
