import { createHash, randomBytes, timingSafeEqual } from 'node:crypto';
import jwt from 'jsonwebtoken';
const ACCESS_TTL_SECONDS = Number(process.env.DBVIEW_JWT_ACCESS_TTL) || 15 * 60;
const REFRESH_TTL_SECONDS = Number(process.env.DBVIEW_JWT_REFRESH_TTL) || 30 * 24 * 60 * 60;
const ISSUER = 'dbview-api';
function getSecret() {
    const s = process.env.DBVIEW_JWT_SECRET;
    if (!s || s.length < 32) {
        throw new Error('DBVIEW_JWT_SECRET env var must be set (>=32 chars).');
    }
    return s;
}
export function signAccessToken(payload) {
    const token = jwt.sign(payload, getSecret(), {
        algorithm: 'HS256',
        expiresIn: ACCESS_TTL_SECONDS,
        issuer: ISSUER,
    });
    return { token, expiresIn: ACCESS_TTL_SECONDS };
}
export function verifyAccessToken(token) {
    const decoded = jwt.verify(token, getSecret(), {
        algorithms: ['HS256'],
        issuer: ISSUER,
    });
    if (typeof decoded !== 'object' || decoded === null) {
        throw new Error('Malformed access token.');
    }
    const { sub, email, role, mustChangePassword } = decoded;
    if (typeof sub !== 'string' ||
        typeof email !== 'string' ||
        (role !== 'admin' && role !== 'user')) {
        throw new Error('Invalid access token claims.');
    }
    return { sub, email, role, mustChangePassword: mustChangePassword === true };
}
export function generateRefreshToken() {
    const raw = randomBytes(48).toString('base64url');
    const hash = hashToken(raw);
    const expiresAt = Date.now() + REFRESH_TTL_SECONDS * 1000;
    return { raw, hash, expiresAt };
}
export function hashToken(raw) {
    return createHash('sha256').update(raw).digest('hex');
}
export function safeCompareHex(a, b) {
    if (a.length !== b.length)
        return false;
    return timingSafeEqual(Buffer.from(a, 'hex'), Buffer.from(b, 'hex'));
}
export const refreshTtlSeconds = REFRESH_TTL_SECONDS;
//# sourceMappingURL=tokens.js.map