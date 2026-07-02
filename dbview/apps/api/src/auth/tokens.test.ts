import { describe, expect, it, beforeAll } from 'vitest';
import { generateRefreshToken, hashToken, signAccessToken, verifyAccessToken } from './tokens.js';

beforeAll(() => {
  process.env.DBVIEW_JWT_SECRET = 'x'.repeat(32);
});

describe('tokens', () => {
  it('signs and verifies access token', () => {
    const { token } = signAccessToken({ sub: 'u1', email: 'a@b.c', role: 'admin' });
    const claims = verifyAccessToken(token);
    expect(claims.sub).toBe('u1');
    expect(claims.role).toBe('admin');
  });

  it('rejects tampered token', () => {
    const { token } = signAccessToken({ sub: 'u1', email: 'a@b.c', role: 'user' });
    expect(() => verifyAccessToken(token + 'x')).toThrow();
  });

  it('refresh token hash is deterministic and matches', () => {
    const a = generateRefreshToken();
    expect(hashToken(a.raw)).toBe(a.hash);
    expect(a.raw).not.toBe(a.hash);
    expect(a.expiresAt).toBeGreaterThan(Date.now());
  });

  it('refresh tokens are unique', () => {
    const a = generateRefreshToken();
    const b = generateRefreshToken();
    expect(a.raw).not.toBe(b.raw);
    expect(a.hash).not.toBe(b.hash);
  });
});
