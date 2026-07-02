import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';
import { ForbiddenError } from '@dbview/shared';
import { AuthService } from './auth.service.js';
import {
  GATEWAY_PASSWORD_SENTINEL,
  isGatewayMode,
  parseGatewayUser,
  verifyGatewaySecret,
  type GatewayUser,
} from './gateway.js';

const tmpDir = mkdtempSync(join(tmpdir(), 'dbview-gateway-'));
const SECRET = 's'.repeat(32);

function encodeUser(user: Record<string, unknown>): string {
  return Buffer.from(JSON.stringify(user), 'utf8').toString('base64url');
}

const CLAIMS: GatewayUser = {
  id: 'a2b8f4a0-0000-4000-8000-000000000001',
  email: 'user@example.com',
  displayName: 'User One',
  role: 'user',
  tenantKey: 'tenant-a',
};

beforeAll(() => {
  process.env.DBVIEW_DATA_DIR = tmpDir;
  process.env.DBVIEW_JWT_SECRET = 'a'.repeat(32);
  delete process.env.DBVIEW_ADMIN_EMAIL;
  delete process.env.DBVIEW_ADMIN_PASSWORD;
});

afterAll(() => {
  rmSync(tmpDir, { recursive: true, force: true });
});

function enableGateway(): void {
  process.env.DBVIEW_GATEWAY_AUTH = 'true';
  process.env.DBVIEW_GATEWAY_SECRET = SECRET;
}

afterEach(() => {
  delete process.env.DBVIEW_GATEWAY_AUTH;
  delete process.env.DBVIEW_GATEWAY_SECRET;
});

describe('gateway mode detection', () => {
  it('is off by default and refuses short secrets', () => {
    expect(isGatewayMode()).toBe(false);
    process.env.DBVIEW_GATEWAY_AUTH = 'true';
    process.env.DBVIEW_GATEWAY_SECRET = 'short';
    expect(isGatewayMode()).toBe(false);
    enableGateway();
    expect(isGatewayMode()).toBe(true);
  });

  it('verifies the shared secret in constant time semantics', () => {
    enableGateway();
    expect(verifyGatewaySecret(SECRET)).toBe(true);
    expect(verifyGatewaySecret('x'.repeat(32))).toBe(false);
    expect(verifyGatewaySecret(undefined)).toBe(false);
  });
});

describe('parseGatewayUser', () => {
  it('round-trips a valid identity header', () => {
    const parsed = parseGatewayUser(encodeUser(CLAIMS));
    expect(parsed).toEqual(CLAIMS);
  });

  it('rejects malformed base64 / JSON / schema violations without throwing', () => {
    expect(parseGatewayUser(undefined)).toBeNull();
    expect(parseGatewayUser('%%%not-base64%%%')).toBeNull();
    expect(parseGatewayUser(Buffer.from('"just a string"').toString('base64url'))).toBeNull();
    expect(parseGatewayUser(encodeUser({ ...CLAIMS, email: 'not-an-email' }))).toBeNull();
    expect(parseGatewayUser(encodeUser({ ...CLAIMS, role: 'superadmin' }))).toBeNull();
  });
});

describe('AuthService in gateway mode', () => {
  it('skips local admin bootstrap and blocks local credential flows', async () => {
    enableGateway();
    const svc = new AuthService();
    await svc.onModuleInit();
    expect(svc.listUsers()).toHaveLength(0);
    await expect(
      svc.login('x@example.com', 'irrelevant-pw', { ip: null, userAgent: null })
    ).rejects.toThrow(ForbiddenError);
    await expect(
      svc.register(
        { email: 'y@example.com', password: 'p'.repeat(12) },
        { ip: null, userAgent: null }
      )
    ).rejects.toThrow(ForbiddenError);
    expect(() => svc.rotate('some-refresh-token', { ip: null, userAgent: null })).toThrow(
      ForbiddenError
    );
    await expect(svc.changePassword(CLAIMS.id, 'a'.repeat(12), 'b'.repeat(12))).rejects.toThrow(
      ForbiddenError
    );
  });

  it('JIT-mirrors gateway identities with an unusable password sentinel', async () => {
    enableGateway();
    const svc = new AuthService();
    await svc.onModuleInit();
    svc.ensureGatewayUser(CLAIMS);
    const stored = svc.getUser(CLAIMS.id);
    expect(stored).toBeDefined();
    expect(stored?.passwordHash).toBe(GATEWAY_PASSWORD_SENTINEL);
    expect(stored?.source).toBe('gateway');
    expect(stored?.tenantKey).toBe('tenant-a');
    expect(stored?.mustChangePassword).toBe(false);
  });

  it('updates the mirror row on role/tenant drift and is idempotent otherwise', async () => {
    enableGateway();
    const svc = new AuthService();
    await svc.onModuleInit();
    svc.ensureGatewayUser(CLAIMS);
    const before = svc.getUser(CLAIMS.id);
    svc.ensureGatewayUser(CLAIMS); // no drift → same object state
    expect(svc.getUser(CLAIMS.id)).toEqual(before);
    svc.ensureGatewayUser({ ...CLAIMS, role: 'admin', tenantKey: 'tenant-b' });
    const after = svc.getUser(CLAIMS.id);
    expect(after?.role).toBe('admin');
    expect(after?.tenantKey).toBe('tenant-b');
  });

  it('confines user listing and tenant checks to the same tenantKey', async () => {
    enableGateway();
    const svc = new AuthService();
    await svc.onModuleInit();
    const other: GatewayUser = {
      ...CLAIMS,
      id: 'a2b8f4a0-0000-4000-8000-000000000002',
      email: 'other@example.com',
      tenantKey: 'tenant-z',
    };
    svc.ensureGatewayUser(CLAIMS);
    svc.ensureGatewayUser(other);
    const visible = svc.listUsersVisibleTo({ tenantKey: CLAIMS.tenantKey });
    expect(visible.map((u) => u.id)).toEqual([CLAIMS.id]);
    expect(svc.sameTenant(other.id, { id: CLAIMS.id, tenantKey: CLAIMS.tenantKey })).toBe(false);
    expect(svc.sameTenant(CLAIMS.id, { id: CLAIMS.id, tenantKey: CLAIMS.tenantKey })).toBe(true);
  });
});
