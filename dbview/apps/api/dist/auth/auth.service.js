var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { Injectable, Logger } from '@nestjs/common';
import { randomBytes, randomUUID } from 'node:crypto';
import { ForbiddenError, InvalidCredentialsError, TokenReplayError, UnauthorizedError, } from '@dbview/shared';
import { UsersStore } from './users.store.js';
import { SessionsStore } from './sessions.store.js';
import { hashPassword, needsRehash, verifyPassword } from './password.js';
import { generateRefreshToken, hashToken, refreshTtlSeconds, signAccessToken } from './tokens.js';
import { toPublicUser } from './auth.types.js';
import { GATEWAY_PASSWORD_SENTINEL, isGatewayMode } from './gateway.js';
import { authEvents } from '../observability/metrics.registry.js';
let AuthService = class AuthService {
    logger = new Logger('AuthService');
    users = new UsersStore();
    sessions = new SessionsStore();
    async onModuleInit() {
        this.sessions.purgeExpired(Date.now());
        if (isGatewayMode()) {
            // Identities are owned by the central IdP and JIT-mirrored on request;
            // seeding a local admin would only create an orphan parallel identity.
            this.logger.log('gateway_mode=on — skipping local admin bootstrap');
            return;
        }
        await this.bootstrapAdmin();
    }
    /**
     * JIT-mirror a gateway-authenticated identity into the local users store so
     * ownership FKs (connections.ownerId, history.ownerId, llm credentials)
     * resolve. Rows carry an unverifiable password sentinel — they can never be
     * used for local login. Persisted only when a field actually drifts.
     */
    ensureGatewayUser(claims) {
        const now = new Date().toISOString();
        const existing = this.users.get(claims.id);
        if (existing) {
            const drifted = existing.email !== claims.email ||
                existing.role !== claims.role ||
                existing.displayName !== (claims.displayName ?? existing.displayName) ||
                (existing.tenantKey ?? null) !== claims.tenantKey ||
                existing.source !== 'gateway' ||
                !existing.isActive;
            if (!drifted)
                return;
            this.users.upsert({
                ...existing,
                email: claims.email,
                emailLower: claims.email.trim().toLowerCase(),
                displayName: claims.displayName ?? existing.displayName,
                role: claims.role,
                isActive: true,
                source: 'gateway',
                tenantKey: claims.tenantKey,
                mustChangePassword: false,
                passwordHash: GATEWAY_PASSWORD_SENTINEL,
            });
            return;
        }
        this.users.upsert({
            id: claims.id,
            email: claims.email,
            emailLower: claims.email.trim().toLowerCase(),
            passwordHash: GATEWAY_PASSWORD_SENTINEL,
            displayName: claims.displayName,
            role: claims.role,
            isActive: true,
            createdAt: now,
            lastLoginAt: now,
            mustChangePassword: false,
            source: 'gateway',
            tenantKey: claims.tenantKey,
        });
        this.logger.log(`gateway_user_mirrored id=${claims.id} role=${claims.role}`);
    }
    async login(email, password, ctx) {
        if (isGatewayMode()) {
            throw new ForbiddenError('Authentication is managed by the central identity provider.');
        }
        const user = this.users.findByEmail(email);
        if (!user || !user.isActive) {
            authEvents.labels({ event: 'login_fail' }).inc();
            this.logger.warn(`login_fail email=${email} ip=${ctx.ip ?? '-'}`);
            throw new InvalidCredentialsError();
        }
        const ok = await verifyPassword(user.passwordHash, password);
        if (!ok) {
            authEvents.labels({ event: 'login_fail' }).inc();
            this.logger.warn(`login_fail email=${email} ip=${ctx.ip ?? '-'}`);
            throw new InvalidCredentialsError();
        }
        if (needsRehash(user.passwordHash)) {
            user.passwordHash = await hashPassword(password);
        }
        user.lastLoginAt = new Date().toISOString();
        this.users.upsert(user);
        authEvents.labels({ event: 'login_success' }).inc();
        this.logger.log(`login_success email=${user.email} role=${user.role}`);
        return this.issueSession(user, randomUUID(), ctx);
    }
    rotate(rawRefresh, ctx) {
        if (isGatewayMode()) {
            throw new ForbiddenError('Authentication is managed by the central identity provider.');
        }
        const presentedHash = hashToken(rawRefresh);
        const session = this.sessions.findByHash(presentedHash);
        if (!session) {
            this.logger.warn(`refresh_unknown ip=${ctx.ip ?? '-'}`);
            throw new UnauthorizedError('Invalid refresh token.');
        }
        if (session.expiresAt < Date.now()) {
            throw new UnauthorizedError('Refresh token expired.');
        }
        if (session.revokedAt !== null) {
            // Replay of revoked token → revoke whole family.
            const n = this.sessions.revokeFamily(session.familyId, Date.now());
            authEvents.labels({ event: 'token_replay' }).inc();
            this.logger.error(`token_replay user=${session.userId} family=${session.familyId} revoked=${n}`);
            throw new TokenReplayError();
        }
        const user = this.users.get(session.userId);
        if (!user || !user.isActive) {
            this.sessions.revokeFamily(session.familyId, Date.now());
            throw new UnauthorizedError('User no longer active.');
        }
        // Mark old session revoked, issue new in same family.
        const newSessionId = randomUUID();
        session.revokedAt = Date.now();
        session.replacedBy = newSessionId;
        this.sessions.update(session);
        authEvents.labels({ event: 'token_rotate' }).inc();
        return this.issueSession(user, session.familyId, ctx, newSessionId);
    }
    isRegistrationEnabled() {
        const v = process.env.DBVIEW_ALLOW_REGISTRATION?.trim().toLowerCase();
        return v === 'true' || v === '1' || v === 'yes' || v === 'on';
    }
    async register(req, ctx) {
        if (isGatewayMode()) {
            throw new ForbiddenError('Authentication is managed by the central identity provider.');
        }
        if (!this.isRegistrationEnabled()) {
            throw new ForbiddenError('Registration is disabled.');
        }
        if (this.users.findByEmail(req.email)) {
            throw new ForbiddenError('Email already in use.');
        }
        const now = new Date().toISOString();
        const user = {
            id: randomUUID(),
            email: req.email,
            emailLower: req.email.trim().toLowerCase(),
            passwordHash: await hashPassword(req.password),
            displayName: req.displayName ?? null,
            role: 'user',
            isActive: true,
            createdAt: now,
            lastLoginAt: now,
            mustChangePassword: false,
        };
        this.users.upsert(user);
        authEvents.labels({ event: 'register' }).inc();
        this.logger.log(`register email=${user.email}`);
        return this.issueSession(user, randomUUID(), ctx);
    }
    logout(rawRefresh) {
        if (!rawRefresh)
            return;
        const session = this.sessions.findByHash(hashToken(rawRefresh));
        if (!session)
            return;
        this.sessions.revokeFamily(session.familyId, Date.now());
        this.logger.log(`logout user=${session.userId} family=${session.familyId}`);
    }
    getUser(id) {
        return this.users.get(id);
    }
    listUsers() {
        return this.users.list().map(toPublicUser);
    }
    /**
     * Users visible to `principal` for admin listing / sharing pickers. In
     * gateway mode visibility is confined to the principal's tenancy scope key
     * (cross-tenant identities must never leak); locally it is the full list.
     */
    listUsersVisibleTo(principal) {
        if (!isGatewayMode())
            return this.listUsers();
        const scope = principal.tenantKey ?? null;
        return this.users
            .list()
            .filter((u) => (u.tenantKey ?? null) === scope)
            .map(toPublicUser);
    }
    /** Whether `userId` belongs to the same tenancy scope as `principal`. */
    sameTenant(userId, principal) {
        if (!isGatewayMode())
            return true;
        if (userId === principal.id)
            return true;
        const target = this.users.get(userId);
        if (!target)
            return false;
        return (target.tenantKey ?? null) === (principal.tenantKey ?? null);
    }
    async invite(req, actorId) {
        if (this.users.findByEmail(req.email)) {
            throw new ForbiddenError(`User already exists: ${req.email}`);
        }
        const now = new Date().toISOString();
        const user = {
            id: randomUUID(),
            email: req.email,
            emailLower: req.email.trim().toLowerCase(),
            passwordHash: await hashPassword(req.password),
            displayName: req.displayName ?? null,
            role: req.role,
            isActive: true,
            createdAt: now,
            lastLoginAt: null,
            mustChangePassword: true,
        };
        this.users.upsert(user);
        this.logger.log(`invite user=${user.email} role=${user.role} by=${actorId}`);
        return toPublicUser(user);
    }
    async updateUser(id, req, actor) {
        const user = this.users.get(id);
        if (!user)
            throw new ForbiddenError(`User not found: ${id}`);
        if (req.role && req.role !== user.role && actor.role !== 'admin') {
            throw new ForbiddenError('Only admins may change roles.');
        }
        if (req.isActive === false && user.id === actor.id) {
            throw new ForbiddenError('Cannot deactivate yourself.');
        }
        if (req.displayName !== undefined)
            user.displayName = req.displayName;
        if (req.role !== undefined)
            user.role = req.role;
        if (req.isActive !== undefined)
            user.isActive = req.isActive;
        if (req.password) {
            user.passwordHash = await hashPassword(req.password);
            user.mustChangePassword = false;
        }
        this.users.upsert(user);
        if (req.isActive === false || req.password) {
            this.sessions.revokeAllForUser(user.id, Date.now());
        }
        this.logger.log(`update_user id=${id} by=${actor.id}`);
        return toPublicUser(user);
    }
    async changePassword(userId, currentPassword, newPassword) {
        if (isGatewayMode()) {
            throw new ForbiddenError('Passwords are managed by the central identity provider.');
        }
        const user = this.users.get(userId);
        if (!user || !user.isActive)
            throw new UnauthorizedError();
        if (currentPassword === newPassword) {
            throw new ForbiddenError('New password must differ from current.');
        }
        const ok = await verifyPassword(user.passwordHash, currentPassword);
        if (!ok) {
            authEvents.labels({ event: 'password_change_fail' }).inc();
            throw new InvalidCredentialsError();
        }
        user.passwordHash = await hashPassword(newPassword);
        user.mustChangePassword = false;
        this.users.upsert(user);
        authEvents.labels({ event: 'password_change_success' }).inc();
        this.logger.log(`password_change user=${user.email}`);
        return toPublicUser(user);
    }
    deleteUser(id, actorId) {
        if (id === actorId)
            throw new ForbiddenError('Cannot delete yourself.');
        const user = this.users.get(id);
        if (!user)
            return;
        this.sessions.revokeAllForUser(id, Date.now());
        this.users.remove(id);
        this.logger.log(`delete_user id=${id} by=${actorId}`);
    }
    issueSession(user, familyId, ctx, sessionId = randomUUID()) {
        const access = signAccessToken({
            sub: user.id,
            email: user.email,
            role: user.role,
            mustChangePassword: user.mustChangePassword,
        });
        const refresh = generateRefreshToken();
        const session = {
            id: sessionId,
            tokenHash: refresh.hash,
            familyId,
            userId: user.id,
            issuedAt: Date.now(),
            expiresAt: refresh.expiresAt,
            revokedAt: null,
            replacedBy: null,
            userAgent: ctx.userAgent,
            ip: ctx.ip,
        };
        this.sessions.insert(session);
        return {
            accessToken: access.token,
            expiresIn: access.expiresIn,
            refreshToken: refresh.raw,
            refreshExpiresAt: refresh.expiresAt,
            user: toPublicUser(user),
        };
    }
    async bootstrapAdmin() {
        if (this.users.count() > 0)
            return;
        const envEmail = process.env.DBVIEW_ADMIN_EMAIL?.trim();
        const envPassword = process.env.DBVIEW_ADMIN_PASSWORD;
        const fromEnv = Boolean(envEmail && envPassword);
        if (envPassword && envPassword.length < 12) {
            throw new Error('DBVIEW_ADMIN_PASSWORD must be at least 12 characters.');
        }
        const email = envEmail || 'admin@dbview.local';
        const password = envPassword ?? randomBytes(18).toString('base64url');
        const mustChangePassword = !fromEnv;
        const now = new Date().toISOString();
        const user = {
            id: randomUUID(),
            email,
            emailLower: email.toLowerCase(),
            passwordHash: await hashPassword(password),
            displayName: 'Admin',
            role: 'admin',
            isActive: true,
            createdAt: now,
            lastLoginAt: null,
            mustChangePassword,
        };
        this.users.upsert(user);
        if (fromEnv) {
            this.logger.log(`bootstrap_admin email=${email} source=env`);
            return;
        }
        const banner = [
            '',
            '╔══════════════════════════════════════════════════════════════════╗',
            '║  dbview — initial admin credentials (printed once, save them!)   ║',
            '╠══════════════════════════════════════════════════════════════════╣',
            `║  email:    ${email.padEnd(54)}║`,
            `║  password: ${password.padEnd(54)}║`,
            '║                                                                  ║',
            '║  You will be forced to change the password on first login.       ║',
            '║  To skip auto-generation, set DBVIEW_ADMIN_EMAIL +               ║',
            '║  DBVIEW_ADMIN_PASSWORD before first boot.                        ║',
            '╚══════════════════════════════════════════════════════════════════╝',
            '',
        ].join('\n');
        process.stdout.write(`${banner}\n`);
        this.logger.log(`bootstrap_admin email=${email} source=generated`);
    }
};
AuthService = __decorate([
    Injectable()
], AuthService);
export { AuthService };
export const refreshCookieTtl = refreshTtlSeconds;
//# sourceMappingURL=auth.service.js.map