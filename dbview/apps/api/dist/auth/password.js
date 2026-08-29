import argon2 from 'argon2';
const ARGON_OPTS = {
    type: argon2.argon2id,
    memoryCost: 19_456,
    timeCost: 2,
    parallelism: 1,
};
export async function hashPassword(plain) {
    return argon2.hash(plain, ARGON_OPTS);
}
export async function verifyPassword(hash, plain) {
    try {
        return await argon2.verify(hash, plain, ARGON_OPTS);
    }
    catch {
        return false;
    }
}
export function needsRehash(hash) {
    return argon2.needsRehash(hash, ARGON_OPTS);
}
//# sourceMappingURL=password.js.map