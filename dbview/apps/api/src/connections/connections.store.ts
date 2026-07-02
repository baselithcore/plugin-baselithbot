import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import type { ConnectionConfig, ConnectionSharing } from '@dbview/shared';

export interface StoredConnection extends ConnectionConfig {
  connectionStringCipher: string;
}

/** Loose shape used while reading legacy `connections.json` files. */
type RawStoredConnection = Partial<StoredConnection> & {
  id: string;
  connectionStringCipher: string;
};

/**
 * Persistence schema versions:
 * - 1: pre-tenant-isolation. Some entries lack `ownerId`/`sharing` (legacy).
 *      All admins implicitly saw every connection — `private` meant nothing
 *      between admins.
 * - 2: ownership is enforced. `private` is strictly owner-only. Entries that
 *      were `private` under v1 are migrated to `admins` to preserve the
 *      operational expectation that other admins could see them.
 */
type SchemaVersion = 1 | 2;

interface FileShape {
  version: SchemaVersion;
  connections: RawStoredConnection[];
}

function defaultPath(): string {
  return resolve(process.env.DBVIEW_DATA_DIR ?? './data', 'connections.json');
}

const DEFAULT_SHARING: ConnectionSharing = { mode: 'private', userIds: [] };

const CURRENT_SCHEMA_VERSION: SchemaVersion = 2;

export class ConnectionsStore {
  private connections: Map<string, StoredConnection> = new Map();
  private legacyIds: Set<string> = new Set();
  private privateUpgradeIds: Set<string> = new Set();
  private loadedVersion: SchemaVersion = CURRENT_SCHEMA_VERSION;
  private readonly filePath: string;

  constructor(filePath?: string) {
    this.filePath = filePath ?? defaultPath();
    this.load();
  }

  list(): StoredConnection[] {
    return [...this.connections.values()];
  }

  get(id: string): StoredConnection | undefined {
    return this.connections.get(id);
  }

  upsert(c: StoredConnection): void {
    this.connections.set(c.id, c);
    this.legacyIds.delete(c.id);
    this.privateUpgradeIds.delete(c.id);
    this.persist();
  }

  remove(id: string): boolean {
    const ok = this.connections.delete(id);
    if (ok) {
      this.legacyIds.delete(id);
      this.privateUpgradeIds.delete(id);
      this.persist();
    }
    return ok;
  }

  /**
   * Returns ids of entries loaded without `ownerId`/`sharing` — they were
   * written before tenant isolation existed. Service backfills these on
   * boot using the first admin as fallback owner.
   */
  pendingLegacyIds(): string[] {
    return [...this.legacyIds];
  }

  /**
   * Ids of v1 entries that were `sharing.mode === 'private'` at load time.
   * Under v1 semantics every admin still saw them; v2 makes `private` truly
   * owner-only, so to avoid a regression for installs with >1 admin these
   * are re-tagged `admins` by the service on first boot.
   */
  pendingPrivateUpgradeIds(): string[] {
    return [...this.privateUpgradeIds];
  }

  loadedSchemaVersion(): SchemaVersion {
    return this.loadedVersion;
  }

  private load(): void {
    if (!existsSync(this.filePath)) return;
    try {
      const raw = readFileSync(this.filePath, 'utf8');
      const data = JSON.parse(raw) as FileShape;
      if (!Array.isArray(data.connections)) return;
      const fileVersion: SchemaVersion =
        data.version === 2 ? 2 : data.version === 1 ? 1 : CURRENT_SCHEMA_VERSION;
      this.loadedVersion = fileVersion;
      for (const c of data.connections) {
        const isLegacy = !c.ownerId;
        if (isLegacy) this.legacyIds.add(c.id);
        // Placeholder ownerId (`legacy:<id>`) is non-uuid on purpose so the
        // visibility filter rejects it for every user until backfill runs.
        const ownerId = c.ownerId ?? `legacy:${c.id}`;
        const sharing = c.sharing ?? DEFAULT_SHARING;
        // Track v1 private entries with a real owner so the service can
        // upgrade them to `admins` (preserves cross-admin visibility).
        if (fileVersion === 1 && !isLegacy && sharing.mode === 'private') {
          this.privateUpgradeIds.add(c.id);
        }
        const filled = {
          id: c.id,
          name: c.name ?? 'untitled',
          dialect: c.dialect!,
          connectionStringCipher: c.connectionStringCipher,
          paramsCipher: c.paramsCipher,
          displayHost: c.displayHost,
          displayDatabase: c.displayDatabase,
          readOnly: true as const,
          ownerId,
          sharing,
          createdAt: c.createdAt ?? new Date().toISOString(),
        } as StoredConnection;
        this.connections.set(filled.id, filled);
      }
    } catch {
      // Ignore corrupt file; start fresh.
    }
  }

  private persist(): void {
    const dir = dirname(this.filePath);
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    const tmp = `${this.filePath}.tmp`;
    const data: FileShape = {
      version: CURRENT_SCHEMA_VERSION,
      connections: [...this.connections.values()],
    };
    writeFileSync(tmp, JSON.stringify(data, null, 2), { mode: 0o600 });
    renameSync(tmp, this.filePath);
  }
}
