import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import type { Role } from '@dbview/shared';

export interface StoredUser {
  id: string;
  email: string;
  emailLower: string;
  passwordHash: string;
  displayName: string | null;
  role: Role;
  isActive: boolean;
  createdAt: string;
  lastLoginAt: string | null;
  mustChangePassword: boolean;
}

interface FileShape {
  version: 1;
  users: StoredUser[];
}

function defaultPath(): string {
  return resolve(process.env.DBVIEW_DATA_DIR ?? './data', 'users.json');
}

export class UsersStore {
  private byId: Map<string, StoredUser> = new Map();
  private byEmail: Map<string, string> = new Map();
  private readonly filePath: string;

  constructor(filePath?: string) {
    this.filePath = filePath ?? defaultPath();
    this.load();
  }

  list(): StoredUser[] {
    return [...this.byId.values()];
  }

  count(): number {
    return this.byId.size;
  }

  get(id: string): StoredUser | undefined {
    return this.byId.get(id);
  }

  findByEmail(email: string): StoredUser | undefined {
    const id = this.byEmail.get(email.trim().toLowerCase());
    return id ? this.byId.get(id) : undefined;
  }

  upsert(u: StoredUser): void {
    const prev = this.byId.get(u.id);
    if (prev && prev.emailLower !== u.emailLower) {
      this.byEmail.delete(prev.emailLower);
    }
    this.byId.set(u.id, u);
    this.byEmail.set(u.emailLower, u.id);
    this.persist();
  }

  remove(id: string): boolean {
    const prev = this.byId.get(id);
    if (!prev) return false;
    this.byId.delete(id);
    this.byEmail.delete(prev.emailLower);
    this.persist();
    return true;
  }

  private load(): void {
    if (!existsSync(this.filePath)) return;
    try {
      const raw = readFileSync(this.filePath, 'utf8');
      const data = JSON.parse(raw) as FileShape;
      if (data.version !== 1 || !Array.isArray(data.users)) return;
      for (const u of data.users) {
        const migrated: StoredUser = { ...u, mustChangePassword: u.mustChangePassword ?? false };
        this.byId.set(migrated.id, migrated);
        this.byEmail.set(migrated.emailLower, migrated.id);
      }
    } catch {
      // Corrupt file: start fresh.
    }
  }

  private persist(): void {
    const dir = dirname(this.filePath);
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    const tmp = `${this.filePath}.tmp`;
    const data: FileShape = { version: 1, users: [...this.byId.values()] };
    writeFileSync(tmp, JSON.stringify(data, null, 2), { mode: 0o600 });
    renameSync(tmp, this.filePath);
  }
}
