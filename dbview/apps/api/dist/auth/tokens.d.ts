import type { Role } from '@dbview/shared';
export interface AccessTokenPayload {
    sub: string;
    email: string;
    role: Role;
    mustChangePassword?: boolean;
}
export declare function signAccessToken(payload: AccessTokenPayload): {
    token: string;
    expiresIn: number;
};
export declare function verifyAccessToken(token: string): AccessTokenPayload;
export interface RefreshTokenBundle {
    raw: string;
    hash: string;
    expiresAt: number;
}
export declare function generateRefreshToken(): RefreshTokenBundle;
export declare function hashToken(raw: string): string;
export declare function safeCompareHex(a: string, b: string): boolean;
export declare const refreshTtlSeconds: number;
//# sourceMappingURL=tokens.d.ts.map