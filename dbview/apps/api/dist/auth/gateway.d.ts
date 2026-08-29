import { z } from 'zod';
/**
 * Gateway (SSO) auth mode — used when dbview runs embedded behind a trusted
 * reverse proxy that authenticates users against a central identity provider
 * (e.g. the BaselithCore `auth` plugin) and forwards the resolved identity.
 *
 * Enabled only when BOTH env vars are set:
 *   - DBVIEW_GATEWAY_AUTH   truthy ('true'|'1'|'yes'|'on')
 *   - DBVIEW_GATEWAY_SECRET shared secret (>=16 chars) known only to the proxy
 *
 * The proxy sends, on every authenticated request:
 *   - x-dbview-gateway-secret: <shared secret>
 *   - x-dbview-gateway-user:   base64url(JSON GatewayUser)
 *
 * With gateway mode OFF (the default), everything in this module is inert and
 * dbview behaves exactly as standalone (local JWT auth). The proxy MUST strip
 * inbound x-dbview-gateway-* headers from client traffic; the shared secret is
 * the defence-in-depth for direct upstream access.
 */
export declare const GatewayUserSchema: z.ZodObject<{
    id: z.ZodString;
    email: z.ZodString;
    displayName: z.ZodDefault<z.ZodNullable<z.ZodString>>;
    role: z.ZodEnum<["admin", "user"]>;
    /**
     * Opaque tenancy scope key resolved by the host (identity-derived; never
     * client-supplied). Sharing between users is confined to the same key.
     */
    tenantKey: z.ZodDefault<z.ZodNullable<z.ZodString>>;
}, "strip", z.ZodTypeAny, {
    id: string;
    email: string;
    role: "admin" | "user";
    displayName: string | null;
    tenantKey: string | null;
}, {
    id: string;
    email: string;
    role: "admin" | "user";
    displayName?: string | null | undefined;
    tenantKey?: string | null | undefined;
}>;
export type GatewayUser = z.infer<typeof GatewayUserSchema>;
export declare const GATEWAY_SECRET_HEADER = "x-dbview-gateway-secret";
export declare const GATEWAY_USER_HEADER = "x-dbview-gateway-user";
/** Sentinel stored as passwordHash on JIT-mirrored rows; never verifiable. */
export declare const GATEWAY_PASSWORD_SENTINEL = "!gateway-sso!";
export declare function gatewaySecret(): string | null;
export declare function isGatewayMode(): boolean;
export declare function verifyGatewaySecret(provided: string | undefined): boolean;
/**
 * Decode + validate the forwarded identity header. Returns null on any
 * malformed input — the caller then simply leaves the request unauthenticated
 * (downstream guards reject it), never throws a 500 on garbage.
 */
export declare function parseGatewayUser(headerValue: string | undefined): GatewayUser | null;
//# sourceMappingURL=gateway.d.ts.map