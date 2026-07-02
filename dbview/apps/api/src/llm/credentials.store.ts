import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import type { RemoteLlmProvider } from '@dbview/shared';

export interface StoredCredential {
  userId: string;
  provider: RemoteLlmProvider;
  cipher: string;
  /** Last 4 chars of the plaintext key (UI-only hint). Never the full key. */
  maskedTail: string;
  createdAt: string;
  updatedAt: string;
}

interface FileShape {
  version: 1;
  credentials: StoredCredential[];
}

function defaultPath(): string {
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
  private readonly filePath: string;
  /** key = `${userId}:${provider}` */
  private credentials: Map<string, StoredCredential> = new Map();

  constructor(filePath?: string) {
    this.filePath = filePath ?? defaultPath();
    this.load();
  }

  get(userId: string, provider: RemoteLlmProvider): StoredCredential | undefined {
    return this.credentials.get(key(userId, provider));
  }

  upsert(c: StoredCredential): void {
    this.credentials.set(key(c.userId, c.provider), c);
    this.persist();
  }

  remove(userId: string, provider: RemoteLlmProvider): boolean {
    const ok = this.credentials.delete(key(userId, provider));
    if (ok) this.persist();
    return ok;
  }

  private load(): void {
    if (!existsSync(this.filePath)) return;
    try {
      const raw = readFileSync(this.filePath, 'utf8');
      const data = JSON.parse(raw) as FileShape;
      if (!Array.isArray(data.credentials)) return;
      for (const c of data.credentials) {
        if (!c.userId || !c.provider || !c.cipher) continue;
        this.credentials.set(key(c.userId, c.provider), c);
      }
    } catch {
      // Corrupt file → start empty rather than crash boot. User can re-enter keys.
    }
  }

  private persist(): void {
    const dir = dirname(this.filePath);
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    const tmp = `${this.filePath}.tmp`;
    const data: FileShape = {
      version: 1,
      credentials: [...this.credentials.values()],
    };
    writeFileSync(tmp, JSON.stringify(data, null, 2), { mode: 0o600 });
    renameSync(tmp, this.filePath);
  }
}

function key(userId: string, provider: RemoteLlmProvider): string {
  return `${userId}:${provider}`;
}
