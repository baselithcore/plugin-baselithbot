import { z } from 'zod';
export declare const RoleSchema: z.ZodEnum<["admin", "user"]>;
export type Role = z.infer<typeof RoleSchema>;
export declare const UserPublicSchema: z.ZodObject<{
    id: z.ZodString;
    email: z.ZodString;
    displayName: z.ZodNullable<z.ZodString>;
    role: z.ZodEnum<["admin", "user"]>;
    isActive: z.ZodBoolean;
    createdAt: z.ZodString;
    lastLoginAt: z.ZodNullable<z.ZodString>;
    mustChangePassword: z.ZodBoolean;
}, "strip", z.ZodTypeAny, {
    id: string;
    email: string;
    displayName: string | null;
    role: "admin" | "user";
    isActive: boolean;
    createdAt: string;
    lastLoginAt: string | null;
    mustChangePassword: boolean;
}, {
    id: string;
    email: string;
    displayName: string | null;
    role: "admin" | "user";
    isActive: boolean;
    createdAt: string;
    lastLoginAt: string | null;
    mustChangePassword: boolean;
}>;
export type UserPublic = z.infer<typeof UserPublicSchema>;
export declare const LoginRequestSchema: z.ZodObject<{
    email: z.ZodString;
    password: z.ZodString;
}, "strip", z.ZodTypeAny, {
    email: string;
    password: string;
}, {
    email: string;
    password: string;
}>;
export type LoginRequest = z.infer<typeof LoginRequestSchema>;
export declare const LoginResponseSchema: z.ZodObject<{
    accessToken: z.ZodString;
    expiresIn: z.ZodNumber;
    user: z.ZodObject<{
        id: z.ZodString;
        email: z.ZodString;
        displayName: z.ZodNullable<z.ZodString>;
        role: z.ZodEnum<["admin", "user"]>;
        isActive: z.ZodBoolean;
        createdAt: z.ZodString;
        lastLoginAt: z.ZodNullable<z.ZodString>;
        mustChangePassword: z.ZodBoolean;
    }, "strip", z.ZodTypeAny, {
        id: string;
        email: string;
        displayName: string | null;
        role: "admin" | "user";
        isActive: boolean;
        createdAt: string;
        lastLoginAt: string | null;
        mustChangePassword: boolean;
    }, {
        id: string;
        email: string;
        displayName: string | null;
        role: "admin" | "user";
        isActive: boolean;
        createdAt: string;
        lastLoginAt: string | null;
        mustChangePassword: boolean;
    }>;
}, "strip", z.ZodTypeAny, {
    user: {
        id: string;
        email: string;
        displayName: string | null;
        role: "admin" | "user";
        isActive: boolean;
        createdAt: string;
        lastLoginAt: string | null;
        mustChangePassword: boolean;
    };
    accessToken: string;
    expiresIn: number;
}, {
    user: {
        id: string;
        email: string;
        displayName: string | null;
        role: "admin" | "user";
        isActive: boolean;
        createdAt: string;
        lastLoginAt: string | null;
        mustChangePassword: boolean;
    };
    accessToken: string;
    expiresIn: number;
}>;
export type LoginResponse = z.infer<typeof LoginResponseSchema>;
export declare const RefreshResponseSchema: z.ZodObject<{
    accessToken: z.ZodString;
    expiresIn: z.ZodNumber;
    user: z.ZodObject<{
        id: z.ZodString;
        email: z.ZodString;
        displayName: z.ZodNullable<z.ZodString>;
        role: z.ZodEnum<["admin", "user"]>;
        isActive: z.ZodBoolean;
        createdAt: z.ZodString;
        lastLoginAt: z.ZodNullable<z.ZodString>;
        mustChangePassword: z.ZodBoolean;
    }, "strip", z.ZodTypeAny, {
        id: string;
        email: string;
        displayName: string | null;
        role: "admin" | "user";
        isActive: boolean;
        createdAt: string;
        lastLoginAt: string | null;
        mustChangePassword: boolean;
    }, {
        id: string;
        email: string;
        displayName: string | null;
        role: "admin" | "user";
        isActive: boolean;
        createdAt: string;
        lastLoginAt: string | null;
        mustChangePassword: boolean;
    }>;
}, "strip", z.ZodTypeAny, {
    user: {
        id: string;
        email: string;
        displayName: string | null;
        role: "admin" | "user";
        isActive: boolean;
        createdAt: string;
        lastLoginAt: string | null;
        mustChangePassword: boolean;
    };
    accessToken: string;
    expiresIn: number;
}, {
    user: {
        id: string;
        email: string;
        displayName: string | null;
        role: "admin" | "user";
        isActive: boolean;
        createdAt: string;
        lastLoginAt: string | null;
        mustChangePassword: boolean;
    };
    accessToken: string;
    expiresIn: number;
}>;
export type RefreshResponse = z.infer<typeof RefreshResponseSchema>;
export declare const InviteRequestSchema: z.ZodObject<{
    email: z.ZodString;
    displayName: z.ZodOptional<z.ZodString>;
    role: z.ZodDefault<z.ZodEnum<["admin", "user"]>>;
    password: z.ZodString;
}, "strip", z.ZodTypeAny, {
    email: string;
    role: "admin" | "user";
    password: string;
    displayName?: string | undefined;
}, {
    email: string;
    password: string;
    displayName?: string | undefined;
    role?: "admin" | "user" | undefined;
}>;
export type InviteRequest = z.infer<typeof InviteRequestSchema>;
export declare const UpdateUserRequestSchema: z.ZodObject<{
    displayName: z.ZodOptional<z.ZodString>;
    role: z.ZodOptional<z.ZodEnum<["admin", "user"]>>;
    isActive: z.ZodOptional<z.ZodBoolean>;
    password: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    displayName?: string | undefined;
    role?: "admin" | "user" | undefined;
    isActive?: boolean | undefined;
    password?: string | undefined;
}, {
    displayName?: string | undefined;
    role?: "admin" | "user" | undefined;
    isActive?: boolean | undefined;
    password?: string | undefined;
}>;
export type UpdateUserRequest = z.infer<typeof UpdateUserRequestSchema>;
export declare const MeResponseSchema: z.ZodObject<{
    user: z.ZodObject<{
        id: z.ZodString;
        email: z.ZodString;
        displayName: z.ZodNullable<z.ZodString>;
        role: z.ZodEnum<["admin", "user"]>;
        isActive: z.ZodBoolean;
        createdAt: z.ZodString;
        lastLoginAt: z.ZodNullable<z.ZodString>;
        mustChangePassword: z.ZodBoolean;
    }, "strip", z.ZodTypeAny, {
        id: string;
        email: string;
        displayName: string | null;
        role: "admin" | "user";
        isActive: boolean;
        createdAt: string;
        lastLoginAt: string | null;
        mustChangePassword: boolean;
    }, {
        id: string;
        email: string;
        displayName: string | null;
        role: "admin" | "user";
        isActive: boolean;
        createdAt: string;
        lastLoginAt: string | null;
        mustChangePassword: boolean;
    }>;
}, "strip", z.ZodTypeAny, {
    user: {
        id: string;
        email: string;
        displayName: string | null;
        role: "admin" | "user";
        isActive: boolean;
        createdAt: string;
        lastLoginAt: string | null;
        mustChangePassword: boolean;
    };
}, {
    user: {
        id: string;
        email: string;
        displayName: string | null;
        role: "admin" | "user";
        isActive: boolean;
        createdAt: string;
        lastLoginAt: string | null;
        mustChangePassword: boolean;
    };
}>;
export type MeResponse = z.infer<typeof MeResponseSchema>;
export declare const RegisterRequestSchema: z.ZodObject<{
    email: z.ZodString;
    password: z.ZodString;
    displayName: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    email: string;
    password: string;
    displayName?: string | undefined;
}, {
    email: string;
    password: string;
    displayName?: string | undefined;
}>;
export type RegisterRequest = z.infer<typeof RegisterRequestSchema>;
export declare const AuthConfigSchema: z.ZodObject<{
    registrationEnabled: z.ZodBoolean;
    /**
     * True when the API runs behind a trusted authenticating gateway (central
     * SSO): local login/registration/password flows are disabled and the SPA
     * must attach the central access token instead. Optional + defaulted so
     * standalone clients/tests parsing older payloads keep working.
     */
    gateway: z.ZodDefault<z.ZodOptional<z.ZodBoolean>>;
}, "strip", z.ZodTypeAny, {
    registrationEnabled: boolean;
    gateway: boolean;
}, {
    registrationEnabled: boolean;
    gateway?: boolean | undefined;
}>;
export type AuthConfig = z.infer<typeof AuthConfigSchema>;
export declare const ChangePasswordRequestSchema: z.ZodObject<{
    currentPassword: z.ZodString;
    newPassword: z.ZodString;
}, "strip", z.ZodTypeAny, {
    currentPassword: string;
    newPassword: string;
}, {
    currentPassword: string;
    newPassword: string;
}>;
export type ChangePasswordRequest = z.infer<typeof ChangePasswordRequestSchema>;
//# sourceMappingURL=auth.d.ts.map