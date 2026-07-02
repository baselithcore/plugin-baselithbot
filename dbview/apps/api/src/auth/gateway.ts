import { timingSafeEqual } from 'node:crypto';
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

export const GatewayUserSchema = z.object({
  id: z.string().min(1).max(128),
  email: z.string().email(),
  displayName: z.string().min(1).max(120).nullable().default(null),
  role: z.enum(['admin', 'user']),
  /**
   * Opaque tenancy scope key resolved by the host (identity-derived; never
   * client-supplied). Sharing between users is confined to the same key.
   */
  tenantKey: z.string().min(1).max(256).nullable().default(null),
});
export type GatewayUser = z.infer<typeof GatewayUserSchema>;

export const GATEWAY_SECRET_HEADER = 'x-dbview-gateway-secret';
export const GATEWAY_USER_HEADER = 'x-dbview-gateway-user';

/** Sentinel stored as passwordHash on JIT-mirrored rows; never verifiable. */
export const GATEWAY_PASSWORD_SENTINEL = '!gateway-sso!';

function truthy(v: string | undefined): boolean {
  const s = v?.trim().toLowerCase();
  return s === 'true' || s === '1' || s === 'yes' || s === 'on';
}

export function gatewaySecret(): string | null {
  const secret = process.env.DBVIEW_GATEWAY_SECRET ?? '';
  return secret.length >= 16 ? secret : null;
}

export function isGatewayMode(): boolean {
  return truthy(process.env.DBVIEW_GATEWAY_AUTH) && gatewaySecret() !== null;
}

export function verifyGatewaySecret(provided: string | undefined): boolean {
  const expected = gatewaySecret();
  if (!expected || !provided) return false;
  const a = Buffer.from(provided);
  const b = Buffer.from(expected);
  if (a.length !== b.length) return false;
  return timingSafeEqual(a, b);
}

/**
 * Decode + validate the forwarded identity header. Returns null on any
 * malformed input — the caller then simply leaves the request unauthenticated
 * (downstream guards reject it), never throws a 500 on garbage.
 */
export function parseGatewayUser(headerValue: string | undefined): GatewayUser | null {
  if (!headerValue) return null;
  let json: unknown;
  try {
    json = JSON.parse(Buffer.from(headerValue, 'base64url').toString('utf8'));
  } catch {
    return null;
  }
  const parsed = GatewayUserSchema.safeParse(json);
  return parsed.success ? parsed.data : null;
}
