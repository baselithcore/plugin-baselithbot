import { mkdtempSync, rmSync, writeFileSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { NotFoundException } from '@nestjs/common';
import { AuthService } from '../auth/auth.service.js';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { ConnectionsService } from './connections.service.js';
import { EnginePool } from '../engine/engine-pool.js';

const tmpDir = mkdtempSync(join(tmpdir(), 'dbview-connsvc-'));

const ADMIN_ID = '00000000-0000-0000-0000-0000000000aa';
const ADMIN_2 = '00000000-0000-0000-0000-0000000000dd';
const USER_A = '00000000-0000-0000-0000-0000000000bb';
const USER_B = '00000000-0000-0000-0000-0000000000cc';

function adminPrincipal(id: string = ADMIN_ID): AuthPrincipal {
  return { id, email: 'admin@x', role: 'admin', source: 'jwt' };
}

function userPrincipal(id: string): AuthPrincipal {
  return { id, email: 'u@x', role: 'user', source: 'jwt' };
}

let svc: ConnectionsService;
let auth: AuthService;

beforeAll(async () => {
  process.env.DBVIEW_DATA_DIR = tmpDir;
  process.env.DBVIEW_JWT_SECRET = 'a'.repeat(32);
  process.env.DBVIEW_SECRET = 'b'.repeat(32);
  process.env.DBVIEW_ADMIN_EMAIL = 'admin@test.local';
  process.env.DBVIEW_ADMIN_PASSWORD = 'super-secret-pw-123';

  // Seed connections.json with one of each sharing mode before service boot
  // so the in-memory store loads them through the normal path.
  mkdirSync(tmpDir, { recursive: true });
  const seed = {
    version: 1,
    connections: [
      {
        id: '11111111-1111-1111-1111-111111111111',
        name: 'private-conn',
        dialect: 'postgres',
        connectionStringCipher: 'ignored-for-list-tests',
        displayHost: 'h',
        displayDatabase: 'd',
        readOnly: true,
        ownerId: ADMIN_ID,
        sharing: { mode: 'private', userIds: [] },
        createdAt: '2026-05-15T00:00:00.000Z',
      },
      {
        id: '22222222-2222-2222-2222-222222222222',
        name: 'all-conn',
        dialect: 'postgres',
        connectionStringCipher: 'ignored',
        displayHost: 'h',
        displayDatabase: 'd',
        readOnly: true,
        ownerId: ADMIN_ID,
        sharing: { mode: 'all', userIds: [] },
        createdAt: '2026-05-15T00:00:00.000Z',
      },
      {
        id: '33333333-3333-3333-3333-333333333333',
        name: 'users-conn',
        dialect: 'postgres',
        connectionStringCipher: 'ignored',
        displayHost: 'h',
        displayDatabase: 'd',
        readOnly: true,
        ownerId: ADMIN_ID,
        sharing: { mode: 'users', userIds: [USER_A] },
        createdAt: '2026-05-15T00:00:00.000Z',
      },
      {
        // Legacy entry, no ownerId/sharing — should be backfilled on init.
        id: '44444444-4444-4444-4444-444444444444',
        name: 'legacy-conn',
        dialect: 'postgres',
        connectionStringCipher: 'ignored',
        displayHost: 'h',
        displayDatabase: 'd',
        readOnly: true,
        createdAt: '2026-05-15T00:00:00.000Z',
      },
    ],
  };
  writeFileSync(join(tmpDir, 'connections.json'), JSON.stringify(seed));

  auth = new AuthService();
  await auth.onModuleInit();

  // Override the bootstrapped admin id by seeding admin manually so the
  // pre-seeded connection ownerIds line up with a real user.
  const adminFromBootstrap = auth.listUsers().find((u) => u.role === 'admin');
  expect(adminFromBootstrap).toBeDefined();

  // Replace store's admin with our known ADMIN_ID so canView+backfill match
  // the seed data above. Simulates a deployment that already has known users.
  const usersStorePath = join(tmpDir, 'users.json');
  const usersFile = {
    version: 1,
    users: [
      {
        id: ADMIN_ID,
        email: 'admin@test.local',
        emailLower: 'admin@test.local',
        passwordHash: adminFromBootstrap!.id /* anything — not validated here */,
        displayName: 'Admin',
        role: 'admin',
        isActive: true,
        createdAt: '2026-05-15T00:00:00.000Z',
        lastLoginAt: null,
        mustChangePassword: false,
      },
      {
        id: USER_A,
        email: 'a@test',
        emailLower: 'a@test',
        passwordHash: 'x',
        displayName: 'A',
        role: 'user',
        isActive: true,
        createdAt: '2026-05-15T00:00:00.000Z',
        lastLoginAt: null,
        mustChangePassword: false,
      },
      {
        id: ADMIN_2,
        email: 'admin2@test',
        emailLower: 'admin2@test',
        passwordHash: 'x',
        displayName: 'Admin2',
        role: 'admin',
        isActive: true,
        createdAt: '2026-05-15T00:00:00.000Z',
        lastLoginAt: null,
        mustChangePassword: false,
      },
      {
        id: USER_B,
        email: 'b@test',
        emailLower: 'b@test',
        passwordHash: 'x',
        displayName: 'B',
        role: 'user',
        isActive: true,
        createdAt: '2026-05-15T00:00:00.000Z',
        lastLoginAt: null,
        mustChangePassword: false,
      },
    ],
  };
  writeFileSync(usersStorePath, JSON.stringify(usersFile));

  // Fresh AuthService picks up the seeded users.json
  auth = new AuthService();
  await auth.onModuleInit();

  svc = new ConnectionsService(auth, new EnginePool());
  svc.onModuleInit();
});

afterAll(() => {
  rmSync(tmpDir, { recursive: true, force: true });
});

describe('ConnectionsService visibility', () => {
  it('admin sees every connection (including legacy after backfill)', () => {
    const ids = svc.list(adminPrincipal(ADMIN_ID)).map((c) => c.id);
    expect(ids).toContain('11111111-1111-1111-1111-111111111111');
    expect(ids).toContain('22222222-2222-2222-2222-222222222222');
    expect(ids).toContain('33333333-3333-3333-3333-333333333333');
    expect(ids).toContain('44444444-4444-4444-4444-444444444444');
  });

  it('user sees only connections shared via mode=all or mode=users where they appear; legacy stays admin-private', () => {
    const visibleA = svc.list(userPrincipal(USER_A)).map((c) => c.id);
    expect(visibleA).toContain('22222222-2222-2222-2222-222222222222'); // mode=all
    expect(visibleA).toContain('33333333-3333-3333-3333-333333333333'); // mode=users, A listed
    expect(visibleA).not.toContain('44444444-4444-4444-4444-444444444444'); // legacy → private on backfill
    expect(visibleA).not.toContain('11111111-1111-1111-1111-111111111111'); // private to admin
  });

  it('user not in sharing.userIds list cannot see mode=users connection', () => {
    const visibleB = svc.list(userPrincipal(USER_B)).map((c) => c.id);
    expect(visibleB).toContain('22222222-2222-2222-2222-222222222222'); // mode=all
    expect(visibleB).not.toContain('44444444-4444-4444-4444-444444444444'); // legacy private
    expect(visibleB).not.toContain('33333333-3333-3333-3333-333333333333'); // mode=users only A
    expect(visibleB).not.toContain('11111111-1111-1111-1111-111111111111'); // private
  });

  it('get() throws NotFound for connection the user cannot see (no enumeration)', () => {
    expect(() => svc.get('11111111-1111-1111-1111-111111111111', userPrincipal(USER_A))).toThrow(
      NotFoundException,
    );
    expect(() => svc.get('33333333-3333-3333-3333-333333333333', userPrincipal(USER_B))).toThrow(
      NotFoundException,
    );
  });

  it('get() succeeds for admin on any connection', () => {
    const c = svc.get('11111111-1111-1111-1111-111111111111', adminPrincipal(ADMIN_ID));
    expect(c.name).toBe('private-conn');
  });

  it('updateSharing rejects non-admin', () => {
    expect(() =>
      svc.updateSharing(
        '22222222-2222-2222-2222-222222222222',
        { sharing: { mode: 'private', userIds: [] } },
        userPrincipal(USER_A),
      ),
    ).toThrow(/admin/);
  });

  it('updateSharing flipping a connection to private removes user visibility', () => {
    svc.updateSharing(
      '22222222-2222-2222-2222-222222222222',
      { sharing: { mode: 'private', userIds: [] } },
      adminPrincipal(ADMIN_ID),
    );
    const visibleA = svc.list(userPrincipal(USER_A)).map((c) => c.id);
    expect(visibleA).not.toContain('22222222-2222-2222-2222-222222222222');
    // Restore for any later assertion ordering.
    svc.updateSharing(
      '22222222-2222-2222-2222-222222222222',
      { sharing: { mode: 'all', userIds: [] } },
      adminPrincipal(ADMIN_ID),
    );
  });

  it('second admin sees admins-mode (v1 private migrated) and all/users connections, NOT another admin-owned private', () => {
    // Re-tighten conn 2 to private (owner=ADMIN_ID) for this assertion.
    svc.updateSharing(
      '22222222-2222-2222-2222-222222222222',
      { sharing: { mode: 'private', userIds: [] } },
      adminPrincipal(ADMIN_ID),
    );
    const visible = svc.list(adminPrincipal(ADMIN_2)).map((c) => c.id);
    // conn 1 was v1 'private' → migrated to 'admins' → ADMIN_2 sees it
    expect(visible).toContain('11111111-1111-1111-1111-111111111111');
    // conn 3 mode='users' → ADMIN_2 is not the owner and not in userIds → hidden
    expect(visible).not.toContain('33333333-3333-3333-3333-333333333333');
    // conn 4 legacy backfilled to private/ADMIN_ID → hidden from ADMIN_2
    expect(visible).not.toContain('44444444-4444-4444-4444-444444444444');
    // conn 2 just re-tightened to private/ADMIN_ID → hidden from ADMIN_2
    expect(visible).not.toContain('22222222-2222-2222-2222-222222222222');
    // restore conn 2 to 'all' for later tests
    svc.updateSharing(
      '22222222-2222-2222-2222-222222222222',
      { sharing: { mode: 'all', userIds: [] } },
      adminPrincipal(ADMIN_ID),
    );
  });

  it('get() throws NotFound when a second admin requests a private connection they do not own', () => {
    // Temporarily flip conn 2 to private owned by ADMIN_ID.
    svc.updateSharing(
      '22222222-2222-2222-2222-222222222222',
      { sharing: { mode: 'private', userIds: [] } },
      adminPrincipal(ADMIN_ID),
    );
    expect(() => svc.get('22222222-2222-2222-2222-222222222222', adminPrincipal(ADMIN_2))).toThrow(
      NotFoundException,
    );
    svc.updateSharing(
      '22222222-2222-2222-2222-222222222222',
      { sharing: { mode: 'all', userIds: [] } },
      adminPrincipal(ADMIN_ID),
    );
  });

  it('updateSharing rejects userIds referencing unknown user', () => {
    expect(() =>
      svc.updateSharing(
        '33333333-3333-3333-3333-333333333333',
        { sharing: { mode: 'users', userIds: ['00000000-0000-0000-0000-0000000000ff'] } },
        adminPrincipal(ADMIN_ID),
      ),
    ).toThrow(/unknown or inactive/);
  });
});
