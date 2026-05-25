import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { AuthService } from './auth.service.js';
import { TokenReplayError } from '@dbview/shared';

const tmpDir = mkdtempSync(join(tmpdir(), 'dbview-auth-'));

beforeAll(() => {
  process.env.DBVIEW_DATA_DIR = tmpDir;
  process.env.DBVIEW_JWT_SECRET = 'a'.repeat(32);
  process.env.DBVIEW_ADMIN_EMAIL = 'admin@test.local';
  process.env.DBVIEW_ADMIN_PASSWORD = 'super-secret-pw-123';
});

afterAll(() => {
  rmSync(tmpDir, { recursive: true, force: true });
});

describe('AuthService', () => {
  it('bootstraps admin from env and authenticates', async () => {
    const svc = new AuthService();
    await svc.onModuleInit();
    const result = await svc.login('admin@test.local', 'super-secret-pw-123', {
      ip: '127.0.0.1',
      userAgent: 'test',
    });
    expect(result.user.role).toBe('admin');
    expect(result.accessToken).toBeTruthy();
    expect(result.refreshToken).toBeTruthy();
  });

  it('rotates refresh token and rejects old token (replay → family revoked)', async () => {
    const svc = new AuthService();
    await svc.onModuleInit();
    const first = await svc.login('admin@test.local', 'super-secret-pw-123', {
      ip: null,
      userAgent: null,
    });
    const second = svc.rotate(first.refreshToken, { ip: null, userAgent: null });
    expect(second.refreshToken).not.toBe(first.refreshToken);

    // Replay old token must throw and revoke family.
    expect(() => svc.rotate(first.refreshToken, { ip: null, userAgent: null })).toThrow(
      TokenReplayError,
    );
    // Rotated (second) token also unusable: it's now revoked → replay path.
    expect(() => svc.rotate(second.refreshToken, { ip: null, userAgent: null })).toThrow(
      TokenReplayError,
    );
  });

  it('rejects login for wrong password', async () => {
    const svc = new AuthService();
    await svc.onModuleInit();
    await expect(
      svc.login('admin@test.local', 'wrong', { ip: null, userAgent: null }),
    ).rejects.toThrow();
  });
});
