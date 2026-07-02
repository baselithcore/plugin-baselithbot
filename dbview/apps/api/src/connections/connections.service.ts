import { Injectable, Logger, NotFoundException, OnModuleInit } from '@nestjs/common';
import { randomUUID } from 'node:crypto';
import { resolve } from 'node:path';
import {
  DIALECT_META,
  DbviewError,
  ForbiddenError,
  buildConnectionString,
  parseSalesforceConnection,
  parseSalesforceDataCloudConnection,
  type ConnectionSharing,
  type ConnectionSummary,
  type CreateConnectionDto,
  type Dialect,
  type UpdateConnectionSharingDto,
  type UploadDumpRequest,
  type UploadDumpResponse,
} from '@dbview/shared';
import { applySqliteSqlDump, writeSqliteDbFile } from '@dbview/sql-core';
import { parseUltipaConnection } from '@dbview/cypher-core';
import { createQueryEngine } from '../engine/factory.js';
import { EnginePool } from '../engine/engine-pool.js';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { AuthService } from '../auth/auth.service.js';
import { decryptString, encryptString } from './crypto.js';
import { ConnectionsStore, type StoredConnection } from './connections.store.js';

const UPLOAD_SUBDIR = 'uploads';

/**
 * New connections default to `private` (least privilege). Other admins can
 * still see/mutate via the explicit `admins` mode chosen at creation time or
 * via PATCH /sharing afterward. Pre-existing `private` entries from v1 are
 * migrated to `admins` by `backfillLegacyOwnership()` so installs with >1
 * admin do not silently lose access on upgrade.
 */
const DEFAULT_SHARING: ConnectionSharing = { mode: 'private', userIds: [] };

@Injectable()
export class ConnectionsService implements OnModuleInit {
  private readonly logger = new Logger('ConnectionsService');
  private readonly store = new ConnectionsStore();

  constructor(
    private readonly auth: AuthService,
    private readonly enginePool: EnginePool
  ) {}

  onModuleInit(): void {
    this.backfillLegacyOwnership();
  }

  list(principal: AuthPrincipal): ConnectionSummary[] {
    return this.store
      .list()
      .filter((c) => this.canView(c, principal))
      .map(stripCipher);
  }

  get(id: string, principal: AuthPrincipal): ConnectionSummary {
    const c = this.requireById(id);
    if (!this.canView(c, principal)) {
      throw new NotFoundException(`Connection ${id} not found.`);
    }
    return stripCipher(c);
  }

  async create(dto: CreateConnectionDto, principal: AuthPrincipal): Promise<ConnectionSummary> {
    // Controller already enforces @Roles('admin'); double-check for safety.
    if (principal.role !== 'admin') {
      throw new ForbiddenError('Only admins may create connections.');
    }
    const sharing = this.validateSharing(dto.sharing ?? DEFAULT_SHARING, principal);
    const connectionString = this.materialize(dto);
    await this.assertReachable(dto.dialect, connectionString);
    const id = randomUUID();
    const display = parseDisplay(connectionString, dto.dialect);
    const stored: StoredConnection = {
      id,
      name: dto.name,
      dialect: dto.dialect,
      connectionStringCipher: encryptString(connectionString),
      // Persist the structured params (when supplied) so the edit dialog can
      // pre-fill non-secret fields without ever decrypting the connection
      // string on the client. Secrets stay encrypted and merged in on PATCH.
      paramsCipher: dto.params ? encryptString(JSON.stringify(dto.params)) : undefined,
      displayHost: display.host,
      displayDatabase: display.database,
      readOnly: true,
      ownerId: principal.id,
      sharing,
      createdAt: new Date().toISOString(),
    };
    this.store.upsert(stored);
    this.logger.log(`connection_create id=${id} owner=${principal.id} sharing=${sharing.mode}`);
    return stripCipher(stored);
  }

  updateSharing(
    id: string,
    dto: UpdateConnectionSharingDto,
    principal: AuthPrincipal
  ): ConnectionSummary {
    if (principal.role !== 'admin') {
      throw new ForbiddenError('Only admins may change connection sharing.');
    }
    const c = this.requireById(id);
    this.logCrossAdminMutation(c, principal, 'updateSharing');
    const sharing = this.validateSharing(dto.sharing, principal);
    const updated: StoredConnection = { ...c, sharing };
    this.store.upsert(updated);
    this.logger.log(`connection_share id=${id} mode=${sharing.mode} by=${principal.id}`);
    return stripCipher(updated);
  }

  remove(id: string, principal: AuthPrincipal): void {
    if (principal.role !== 'admin') {
      throw new ForbiddenError('Only admins may delete connections.');
    }
    const c = this.store.get(id);
    if (!c) {
      throw new NotFoundException(`Connection ${id} not found.`);
    }
    this.logCrossAdminMutation(c, principal, 'delete');
    try {
      const cs = decryptString(c.connectionStringCipher);
      this.enginePool.invalidate(c.dialect, cs);
    } catch {
      /* ignore — best-effort eviction */
    }
    this.store.remove(id);
  }

  async test(dto: CreateConnectionDto, principal: AuthPrincipal): Promise<{ ok: true }> {
    if (principal.role !== 'admin') {
      throw new ForbiddenError('Only admins may test connections.');
    }
    const connectionString = this.materialize(dto);
    await this.assertReachable(dto.dialect, connectionString);
    return { ok: true };
  }

  uploadDump(req: UploadDumpRequest): UploadDumpResponse {
    let buf: Buffer;
    try {
      buf = Buffer.from(req.contentBase64, 'base64');
    } catch {
      throw new DbviewError('Invalid base64 payload.', 'invalid_dump_payload', 400);
    }
    if (buf.length === 0) {
      throw new DbviewError('Uploaded dump is empty.', 'invalid_dump_payload', 400);
    }
    const dataDir = resolve(process.env.DBVIEW_DATA_DIR ?? './data');
    const id = randomUUID();
    const baseName =
      req.format === 'sqlite-sql' ? `${id}.db` : `${id}-${sanitizeFilename(req.filename)}`;
    const targetPath = resolve(dataDir, UPLOAD_SUBDIR, baseName);
    try {
      if (req.format === 'sqlite-db') {
        writeSqliteDbFile(targetPath, buf);
        return { filePath: targetPath, sizeBytes: buf.length };
      }
      const sql = buf.toString('utf8');
      const { tables } = applySqliteSqlDump(targetPath, sql);
      return { filePath: targetPath, sizeBytes: buf.length, tables };
    } catch (err) {
      throw new DbviewError(
        `Dump import failed: ${(err as Error).message}`,
        'dump_import_failed',
        400
      );
    }
  }

  resolvePlain(
    id: string,
    principal: AuthPrincipal
  ): { dialect: Dialect; connectionString: string } {
    const c = this.requireById(id);
    if (!this.canView(c, principal)) {
      throw new NotFoundException(`Connection ${id} not found.`);
    }
    return { dialect: c.dialect, connectionString: decryptString(c.connectionStringCipher) };
  }

  /**
   * Read visibility. Ownership is enforced even for admins: `private` means
   * truly private to the owner. Other modes:
   *   - `admins` → every admin sees it (operational co-op default)
   *   - `all`    → every authenticated user sees it
   *   - `users`  → owner + explicitly listed userIds
   *
   * Mirrors `canResolve` — if you can see the summary you can also resolve
   * the credentials needed to run a query. Splitting them would only confuse
   * users (visible-but-unusable connections).
   */
  private canView(c: StoredConnection, principal: AuthPrincipal): boolean {
    if (c.ownerId === principal.id) return true;
    // Non-owner visibility never crosses a tenancy scope: in gateway (SSO)
    // mode every sharing mode is confined to identities with the same
    // tenantKey as the connection owner. Locally this is always true.
    if (!this.auth.sameTenant(c.ownerId, principal)) return false;
    if (c.sharing.mode === 'all') return true;
    if (c.sharing.mode === 'users' && c.sharing.userIds.includes(principal.id)) return true;
    if (c.sharing.mode === 'admins' && principal.role === 'admin') return true;
    return false;
  }

  /**
   * Audit hook for admin mutations on connections they do not own. We
   * deliberately keep cross-admin mutation allowed for operational recovery
   * (deactivated owners, orphaned connections) but log the event so the
   * audit trail is explicit about who changed someone else's resource.
   */
  private logCrossAdminMutation(
    c: StoredConnection,
    principal: AuthPrincipal,
    action: 'delete' | 'updateSharing'
  ): void {
    if (principal.role !== 'admin' || c.ownerId === principal.id) return;
    this.logger.warn(
      `connection_cross_admin_${action} id=${c.id} owner=${c.ownerId} actor=${principal.id}`
    );
  }

  private requireById(id: string): StoredConnection {
    const c = this.store.get(id);
    if (!c) throw new NotFoundException(`Connection ${id} not found.`);
    return c;
  }

  private validateSharing(sharing: ConnectionSharing, principal: AuthPrincipal): ConnectionSharing {
    if (sharing.mode === 'private' || sharing.mode === 'admins' || sharing.mode === 'all') {
      return { mode: sharing.mode, userIds: [] };
    }
    const unique = [...new Set(sharing.userIds)];
    for (const uid of unique) {
      const user = this.auth.getUser(uid);
      // Explicit grants must also stay inside the actor's tenancy scope in
      // gateway (SSO) mode — a share target from another tenant is treated
      // exactly like an unknown user so ids never leak across tenants.
      if (!user || !user.isActive || !this.auth.sameTenant(uid, principal)) {
        throw new DbviewError(
          `sharing.userIds references unknown or inactive user: ${uid}`,
          'invalid_sharing_target',
          400
        );
      }
    }
    return { mode: 'users', userIds: unique };
  }

  /**
   * Two-phase migration run on boot:
   *
   *   1. Pre-tenant-isolation entries (no `ownerId`/`sharing`) are re-attached
   *      to the first admin and locked down to `private`. Non-admins cannot
   *      inherit the previous global visibility; the owning admin can re-share
   *      via PATCH /api/connections/:id/sharing.
   *
   *   2. v1 `private` entries with a valid owner are re-tagged to `admins` so
   *      cross-admin visibility (the v1 implicit behavior) is preserved under
   *      v2 semantics where `private` is strictly owner-only. Without this,
   *      installations with multiple admins would silently lose access on
   *      upgrade. Owners can re-tighten to `private` at any time.
   */
  private backfillLegacyOwnership(): void {
    const legacyPending = this.store.pendingLegacyIds();
    const privatePending = this.store.pendingPrivateUpgradeIds();
    if (legacyPending.length === 0 && privatePending.length === 0) return;
    const admin = this.auth.listUsers().find((u) => u.role === 'admin' && u.isActive);
    if (!admin) {
      this.logger.warn(
        `legacy_connections_pending count=${legacyPending.length + privatePending.length} no_admin_yet — will retry on first access`
      );
      return;
    }
    for (const id of legacyPending) {
      const c = this.store.get(id);
      if (!c) continue;
      const migrated: StoredConnection = {
        ...c,
        ownerId: admin.id,
        sharing: { mode: 'private', userIds: [] },
      };
      this.store.upsert(migrated);
    }
    for (const id of privatePending) {
      const c = this.store.get(id);
      if (!c) continue;
      // Only upgrade if still `private` — operator could have re-shared
      // between load and migration in some race; respect that.
      if (c.sharing.mode !== 'private') continue;
      const migrated: StoredConnection = {
        ...c,
        sharing: { mode: 'admins', userIds: [] },
      };
      this.store.upsert(migrated);
    }
    if (legacyPending.length > 0) {
      this.logger.log(
        `legacy_connections_migrated count=${legacyPending.length} owner=${admin.id}`
      );
    }
    if (privatePending.length > 0) {
      this.logger.log(
        `v1_private_upgraded_to_admins count=${privatePending.length} (preserves cross-admin visibility)`
      );
    }
  }

  private materialize(dto: CreateConnectionDto): string {
    const meta = DIALECT_META[dto.dialect];
    if (!meta.available) {
      throw new DbviewError(
        `Dialect '${dto.dialect}' is not yet available. Coming soon.`,
        'dialect_unavailable',
        400
      );
    }
    if (dto.params) return buildConnectionString(dto.params);
    if (dto.connectionString) return dto.connectionString;
    throw new DbviewError(
      'Either params or connectionString is required.',
      'invalid_connection_payload',
      400
    );
  }

  private async assertReachable(dialect: Dialect, connectionString: string): Promise<void> {
    const engine = createQueryEngine(dialect, connectionString);
    try {
      if (engine.verifyReachable) {
        await engine.verifyReachable();
      } else {
        await engine.introspect();
      }
    } catch (err) {
      throw new DbviewError(
        `Connection test failed: ${(err as Error).message}`,
        'connection_test_failed',
        400
      );
    } finally {
      await engine.close();
    }
  }
}

function stripCipher(c: StoredConnection): ConnectionSummary {
  const { connectionStringCipher: _cs, paramsCipher: _p, ...rest } = c;
  return rest;
}

function sanitizeFilename(name: string): string {
  // Strip path separators and constrain to safe chars; schema validator already enforces.
  return name.replace(/[^A-Za-z0-9._-]/g, '_').slice(0, 100);
}

function parseDisplay(cs: string, dialect: Dialect): { host?: string; database?: string } {
  if (dialect === 'sqlite' || dialect === 'duckdb') return { database: cs.split('/').pop() };
  if (dialect === 'clickhouse') {
    try {
      const u = new URL(cs);
      const db = u.pathname.replace(/^\//, '');
      return { host: u.hostname, database: db || 'default' };
    } catch {
      return {};
    }
  }
  if (dialect === 'ultipa') {
    try {
      const target = parseUltipaConnection(cs);
      const firstHost = target.hosts[0]?.split(':')[0];
      return { host: firstHost, database: target.defaultGraph ?? 'default' };
    } catch {
      return {};
    }
  }
  if (dialect === 'salesforce') {
    try {
      const p = parseSalesforceConnection(cs);
      const u = new URL(p.instanceUrl);
      return { host: u.hostname, database: p.isSandbox ? 'sandbox' : 'production' };
    } catch {
      return {};
    }
  }
  if (dialect === 'salesforce-data-cloud') {
    try {
      const p = parseSalesforceDataCloudConnection(cs);
      const u = new URL(p.loginUrl);
      return { host: u.hostname, database: p.dataspace ?? 'default' };
    } catch {
      return {};
    }
  }
  try {
    const normalized =
      dialect === 'falkordb'
        ? cs.replace(/^falkor:/, 'redis:')
        : dialect === 'mssql'
          ? cs.replace(/^mssql:/, 'http:')
          : dialect === 'oracle'
            ? cs.replace(/^oracle:/, 'http:')
            : cs;
    const u = new URL(normalized);
    const path = u.pathname.replace(/^\//, '');
    let database: string;
    if (dialect === 'neo4j') database = path || 'neo4j';
    else if (dialect === 'falkordb') database = path || 'default';
    else database = path;
    return { host: u.hostname, database };
  } catch {
    return {};
  }
}
