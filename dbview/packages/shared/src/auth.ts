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
  /**
   * True when the API runs behind a trusted authenticating gateway (central
   * SSO): local login/registration/password flows are disabled and the SPA
   * must attach the central access token instead. Optional + defaulted so
   * standalone clients/tests parsing older payloads keep working.
   */
  gateway: z.boolean().optional().default(false),
});
export type AuthConfig = z.infer<typeof AuthConfigSchema>;

export const ChangePasswordRequestSchema = z.object({
  currentPassword: z.string().min(1).max(200),
  newPassword: z.string().min(12).max(200),
});
export type ChangePasswordRequest = z.infer<typeof ChangePasswordRequestSchema>;
