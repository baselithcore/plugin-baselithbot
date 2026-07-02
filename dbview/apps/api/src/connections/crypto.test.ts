import { beforeEach, describe, expect, it } from 'vitest';
import { decryptString, encryptString } from './crypto.js';

describe('connection crypto', () => {
  beforeEach(() => {
    process.env.DBVIEW_SECRET = 'test-secret-please-rotate';
  });

  it('round-trips a plaintext string', () => {
    const plain = 'postgres://user:hunter2@host:5432/db';
    const cipher = encryptString(plain);
    expect(cipher).not.toContain(plain);
    expect(decryptString(cipher)).toBe(plain);
  });

  it('produces different ciphertexts for the same plaintext (random IV)', () => {
    const a = encryptString('same');
    const b = encryptString('same');
    expect(a).not.toBe(b);
    expect(decryptString(a)).toBe('same');
    expect(decryptString(b)).toBe('same');
  });

  it('fails to decrypt with a tampered tag', () => {
    const cipher = encryptString('value');
    const raw = Buffer.from(cipher, 'base64');
    // Flip one bit inside the auth tag region (bytes 12..28).
    raw[14] = (raw[14] ?? 0) ^ 0xff;
    const tampered = raw.toString('base64');
    expect(() => decryptString(tampered)).toThrow();
  });

  it('fails when DBVIEW_SECRET is missing', () => {
    delete process.env.DBVIEW_SECRET;
    expect(() => encryptString('x')).toThrow(/DBVIEW_SECRET/);
  });

  it('fails when DBVIEW_SECRET is shorter than 16 chars', () => {
    process.env.DBVIEW_SECRET = 'short';
    expect(() => encryptString('x')).toThrow(/16/);
  });

  it('decryption fails when DBVIEW_SECRET changes between encrypt and decrypt', () => {
    process.env.DBVIEW_SECRET = 'first-key-please-rotate';
    const cipher = encryptString('payload');
    process.env.DBVIEW_SECRET = 'second-key-please-rotate';
    expect(() => decryptString(cipher)).toThrow();
  });
});
