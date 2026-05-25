import { z } from 'zod';

export const RoleSchema = z.enum(['admin', 'user']);
export type Role = z.infer<typeof RoleSchema>;

export const UserPublicSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  displayName: z.string().min(1).max(120).nullable(),
  role: RoleSchema,
  isActive: z.boolean(),
  createdAt: z.string().datetime(),
  lastLoginAt: z.string().datetime().nullable(),
  mustChangePassword: z.boolean(),
});
export type UserPublic = z.infer<typeof UserPublicSchema>;

export const LoginRequestSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1).max(200),
});
export type LoginRequest = z.infer<typeof LoginRequestSchema>;

export const LoginResponseSchema = z.object({
  accessToken: z.string(),
  expiresIn: z.number().int().positive(),
  user: UserPublicSchema,
});
export type LoginResponse = z.infer<typeof LoginResponseSchema>;

export const RefreshResponseSchema = LoginResponseSchema;
export type RefreshResponse = z.infer<typeof RefreshResponseSchema>;

export const InviteRequestSchema = z.object({
  email: z.string().email(),
  displayName: z.string().min(1).max(120).optional(),
  role: RoleSchema.default('user'),
  password: z.string().min(12).max(200),
});
export type InviteRequest = z.infer<typeof InviteRequestSchema>;

export const UpdateUserRequestSchema = z.object({
  displayName: z.string().min(1).max(120).optional(),
  role: RoleSchema.optional(),
  isActive: z.boolean().optional(),
  password: z.string().min(12).max(200).optional(),
});
export type UpdateUserRequest = z.infer<typeof UpdateUserRequestSchema>;

export const MeResponseSchema = z.object({ user: UserPublicSchema });
export type MeResponse = z.infer<typeof MeResponseSchema>;

export const RegisterRequestSchema = z.object({
  email: z.string().email(),
  password: z.string().min(12).max(200),
  displayName: z.string().min(1).max(120).optional(),
});
export type RegisterRequest = z.infer<typeof RegisterRequestSchema>;

export const AuthConfigSchema = z.object({
  registrationEnabled: z.boolean(),
});
export type AuthConfig = z.infer<typeof AuthConfigSchema>;

export const ChangePasswordRequestSchema = z.object({
  currentPassword: z.string().min(1).max(200),
  newPassword: z.string().min(12).max(200),
});
export type ChangePasswordRequest = z.infer<typeof ChangePasswordRequestSchema>;

/**
 * First-boot superuser bootstrap. Mirrors the wikigen contract:
 * - GET /api/auth/bootstrap/status — public, returns `needsBootstrap` flag.
 * - POST /api/auth/bootstrap — loopback-only when `users_count == 0`,
 *   creates the first admin and issues a session in one shot.
 *
 * Endpoint hardening (controller side): rate-limited, loopback-only,
 * idempotent (rejects if any user already exists). Once a superuser
 * exists the wizard never appears again and additional admins are
 * managed via the standard invite flow.
 */
export const BootstrapStatusResponseSchema = z.object({
  needsBootstrap: z.boolean(),
  usersCount: z.number().int().nonnegative(),
});
export type BootstrapStatusResponse = z.infer<typeof BootstrapStatusResponseSchema>;

export const BootstrapRequestSchema = z.object({
  email: z.string().email(),
  password: z.string().min(12).max(200),
  displayName: z.string().min(1).max(120).optional(),
});
export type BootstrapRequest = z.infer<typeof BootstrapRequestSchema>;
