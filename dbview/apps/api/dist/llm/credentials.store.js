import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
function defaultPath() {
    return resolve(process.env.DBVIEW_DATA_DIR ?? './data', 'llm-credentials.json');
}
/**
 * Persistence layer for per-user LLM API keys.
 *
 * On-disk shape mirrors connections.json: atomic write via tmp+rename, mode
 * 0600, JSON. Ciphertext only — plaintext keys are never written. Decryption
 * happens in {@link LlmCredentialsService}, not here.
 */
export class LlmCredentialsStore {
    filePath;
    /** key = `${userId}:${provider}` */
    credentials = new Map();
    constructor(filePath) {
        this.filePath = filePath ?? defaultPath();
        this.load();
    }
    get(userId, provider) {
        return this.credentials.get(key(userId, provider));
    }
    upsert(c) {
        this.credentials.set(key(c.userId, c.provider), c);
        this.persist();
    }
    remove(userId, provider) {
        const ok = this.credentials.delete(key(userId, provider));
        if (ok)
            this.persist();
        return ok;
    }
    load() {
        if (!existsSync(this.filePath))
            return;
        try {
            const raw = readFileSync(this.filePath, 'utf8');
            const data = JSON.parse(raw);
            if (!Array.isArray(data.credentials))
                return;
            for (const c of data.credentials) {
                if (!c.userId || !c.provider || !c.cipher)
                    continue;
                this.credentials.set(key(c.userId, c.provider), c);
            }
        }
        catch {
            // Corrupt file → start empty rather than crash boot. User can re-enter keys.
        }
    }
    persist() {
        const dir = dirname(this.filePath);
        if (!existsSync(dir))
            mkdirSync(dir, { recursive: true });
        const tmp = `${this.filePath}.tmp`;
        const data = {
            version: 1,
            credentials: [...this.credentials.values()],
        };
        writeFileSync(tmp, JSON.stringify(data, null, 2), { mode: 0o600 });
        renameSync(tmp, this.filePath);
    }
}
function key(userId, provider) {
    return `${userId}:${provider}`;
}
//# sourceMappingURL=credentials.store.js.map