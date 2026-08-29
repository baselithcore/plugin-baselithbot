import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
function defaultPath() {
    return resolve(process.env.DBVIEW_DATA_DIR ?? './data', 'users.json');
}
export class UsersStore {
    byId = new Map();
    byEmail = new Map();
    filePath;
    constructor(filePath) {
        this.filePath = filePath ?? defaultPath();
        this.load();
    }
    list() {
        return [...this.byId.values()];
    }
    count() {
        return this.byId.size;
    }
    get(id) {
        return this.byId.get(id);
    }
    findByEmail(email) {
        const id = this.byEmail.get(email.trim().toLowerCase());
        return id ? this.byId.get(id) : undefined;
    }
    upsert(u) {
        const prev = this.byId.get(u.id);
        if (prev && prev.emailLower !== u.emailLower) {
            this.byEmail.delete(prev.emailLower);
        }
        this.byId.set(u.id, u);
        this.byEmail.set(u.emailLower, u.id);
        this.persist();
    }
    remove(id) {
        const prev = this.byId.get(id);
        if (!prev)
            return false;
        this.byId.delete(id);
        this.byEmail.delete(prev.emailLower);
        this.persist();
        return true;
    }
    load() {
        if (!existsSync(this.filePath))
            return;
        try {
            const raw = readFileSync(this.filePath, 'utf8');
            const data = JSON.parse(raw);
            if (data.version !== 1 || !Array.isArray(data.users))
                return;
            for (const u of data.users) {
                const migrated = { ...u, mustChangePassword: u.mustChangePassword ?? false };
                this.byId.set(migrated.id, migrated);
                this.byEmail.set(migrated.emailLower, migrated.id);
            }
        }
        catch {
            // Corrupt file: start fresh.
        }
    }
    persist() {
        const dir = dirname(this.filePath);
        if (!existsSync(dir))
            mkdirSync(dir, { recursive: true });
        const tmp = `${this.filePath}.tmp`;
        const data = { version: 1, users: [...this.byId.values()] };
        writeFileSync(tmp, JSON.stringify(data, null, 2), { mode: 0o600 });
        renameSync(tmp, this.filePath);
    }
}
//# sourceMappingURL=users.store.js.map