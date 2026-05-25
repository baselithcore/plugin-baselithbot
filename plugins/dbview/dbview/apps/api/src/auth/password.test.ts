import { describe, expect, it } from 'vitest';
import { hashPassword, needsRehash, verifyPassword } from './password.js';

describe('password', () => {
  it('hashes and verifies a password', async () => {
    const hash = await hashPassword('correct horse battery staple');
    expect(hash).toMatch(/^\$argon2id\$/);
    expect(await verifyPassword(hash, 'correct horse battery staple')).toBe(true);
  });

  it('rejects wrong password', async () => {
    const hash = await hashPassword('one');
    expect(await verifyPassword(hash, 'two')).toBe(false);
  });

  it('returns false on malformed hash instead of throwing', async () => {
    expect(await verifyPassword('not-a-hash', 'whatever')).toBe(false);
  });

  it('needsRehash returns false for current params', async () => {
    const hash = await hashPassword('rotate-me');
    expect(needsRehash(hash)).toBe(false);
  });
});
