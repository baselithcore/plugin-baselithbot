import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

export interface StoredSession {
  id: string;
  tokenHash: string;
  familyId: string;
  userId: string;
  issuedAt: number;
  expiresAt: number;
  revokedAt: number | null;
  replacedBy: string | null;
  userAgent: string | null;
  ip: string | null;
}

interface FileShape {
  version: 1;
  sessions: StoredSession[];
}

function defaultPath(): string {
  return resolve(process.env.DBVIEW_DATA_DIR ?? './data', 'sessions.json');
}

export class SessionsStore {
  private byId: Map<string, StoredSession> = new Map();
  private byHash: Map<string, string> = new Map();
  // Secondary indexes for O(1) bulk-revoke. Maintained on every mutation.
  private byUserId: Map<string, Set<string>> = new Map();
  private byFamilyId: Map<string, Set<string>> = new Map();
  private readonly filePath: string;

  constructor(filePath?: string) {
    this.filePath = filePath ?? defaultPath();
    this.load();
  }

  findByHash(hash: string): StoredSession | undefined {
    const id = this.byHash.get(hash);
    return id ? this.byId.get(id) : undefined;
  }

  insert(s: StoredSession): void {
    this.byId.set(s.id, s);
    this.byHash.set(s.tokenHash, s.id);
    this.indexAdd(s);
    this.persist();
  }

  update(s: StoredSession): void {
    const prev = this.byId.get(s.id);
    if (prev) {
      if (prev.tokenHash !== s.tokenHash) {
        this.byHash.delete(prev.tokenHash);
      }
      this.indexRemove(prev);
    }
    this.byId.set(s.id, s);
    this.byHash.set(s.tokenHash, s.id);
    this.indexAdd(s);
    this.persist();
  }

  revokeFamily(familyId: string, when: number): number {
    const ids = this.byFamilyId.get(familyId);
    if (!ids) return 0;
    let touched = 0;
    for (const id of ids) {
      const s = this.byId.get(id);
      if (s && s.revokedAt === null) {
        s.revokedAt = when;
        touched += 1;
      }
    }
    if (touched > 0) this.persist();
    return touched;
  }

  revokeAllForUser(userId: string, when: number): number {
    const ids = this.byUserId.get(userId);
    if (!ids) return 0;
    let touched = 0;
    for (const id of ids) {
      const s = this.byId.get(id);
      if (s && s.revokedAt === null) {
        s.revokedAt = when;
        touched += 1;
      }
    }
    if (touched > 0) this.persist();
    return touched;
  }

  purgeExpired(now: number): number {
    let removed = 0;
    for (const [id, s] of this.byId) {
      if (s.expiresAt < now) {
        this.byId.delete(id);
        this.byHash.delete(s.tokenHash);
        this.indexRemove(s);
        removed += 1;
      }
    }
    if (removed > 0) this.persist();
    return removed;
  }

  private indexAdd(s: StoredSession): void {
    let users = this.byUserId.get(s.userId);
    if (!users) {
      users = new Set();
      this.byUserId.set(s.userId, users);
    }
    users.add(s.id);
    let fam = this.byFamilyId.get(s.familyId);
    if (!fam) {
      fam = new Set();
      this.byFamilyId.set(s.familyId, fam);
    }
    fam.add(s.id);
  }

  private indexRemove(s: StoredSession): void {
    const users = this.byUserId.get(s.userId);
    if (users) {
      users.delete(s.id);
      if (users.size === 0) this.byUserId.delete(s.userId);
    }
    const fam = this.byFamilyId.get(s.familyId);
    if (fam) {
      fam.delete(s.id);
      if (fam.size === 0) this.byFamilyId.delete(s.familyId);
    }
  }

  private load(): void {
    if (!existsSync(this.filePath)) return;
    try {
      const raw = readFileSync(this.filePath, 'utf8');
      const data = JSON.parse(raw) as FileShape;
      if (data.version !== 1 || !Array.isArray(data.sessions)) return;
      for (const s of data.sessions) {
        this.byId.set(s.id, s);
        this.byHash.set(s.tokenHash, s.id);
        this.indexAdd(s);
      }
    } catch {
      // Corrupt file: start fresh.
    }
  }

  private persist(): void {
    const dir = dirname(this.filePath);
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    const tmp = `${this.filePath}.tmp`;
    const data: FileShape = { version: 1, sessions: [...this.byId.values()] };
    writeFileSync(tmp, JSON.stringify(data, null, 2), { mode: 0o600 });
    renameSync(tmp, this.filePath);
  }
}
