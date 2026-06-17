/**
 * WebAuthn / passkey browser client.
 *
 * Bridges the server's (py_webauthn) base64url JSON options to the browser
 * `navigator.credentials` API and serializes the resulting credential back to
 * the JSON shape the server expects.
 */

const API_BASE = '/api/auth/webauthn';

function b64urlToBuf(value: string): ArrayBuffer {
  const pad = '='.repeat((4 - (value.length % 4)) % 4);
  const base64 = (value + pad).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(base64);
  const buf = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) buf[i] = raw.charCodeAt(i);
  return buf.buffer;
}

function bufToB64url(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let str = '';
  for (let i = 0; i < bytes.length; i++) str += String.fromCharCode(bytes[i]);
  return btoa(str).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export function isPasskeySupported(): boolean {
  return typeof window !== 'undefined' && !!window.PublicKeyCredential;
}

async function postJson<T>(path: string, body?: unknown, token?: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    credentials: 'include',
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

/* eslint-disable @typescript-eslint/no-explicit-any */

function decodeCreationOptions(opts: any): PublicKeyCredentialCreationOptions {
  return {
    ...opts,
    challenge: b64urlToBuf(opts.challenge),
    user: { ...opts.user, id: b64urlToBuf(opts.user.id) },
    excludeCredentials: (opts.excludeCredentials || []).map((c: any) => ({
      ...c,
      id: b64urlToBuf(c.id),
    })),
  };
}

function decodeRequestOptions(opts: any): PublicKeyCredentialRequestOptions {
  return {
    ...opts,
    challenge: b64urlToBuf(opts.challenge),
    allowCredentials: (opts.allowCredentials || []).map((c: any) => ({
      ...c,
      id: b64urlToBuf(c.id),
    })),
  };
}

function serializeRegistration(cred: PublicKeyCredential): any {
  const r = cred.response as AuthenticatorAttestationResponse;
  return {
    id: cred.id,
    rawId: bufToB64url(cred.rawId),
    type: cred.type,
    response: {
      attestationObject: bufToB64url(r.attestationObject),
      clientDataJSON: bufToB64url(r.clientDataJSON),
      transports: (r as any).getTransports ? (r as any).getTransports() : [],
    },
    clientExtensionResults: cred.getClientExtensionResults(),
    authenticatorAttachment: (cred as any).authenticatorAttachment,
  };
}

function serializeAssertion(cred: PublicKeyCredential): any {
  const r = cred.response as AuthenticatorAssertionResponse;
  return {
    id: cred.id,
    rawId: bufToB64url(cred.rawId),
    type: cred.type,
    response: {
      authenticatorData: bufToB64url(r.authenticatorData),
      clientDataJSON: bufToB64url(r.clientDataJSON),
      signature: bufToB64url(r.signature),
      userHandle: r.userHandle ? bufToB64url(r.userHandle) : null,
    },
    clientExtensionResults: cred.getClientExtensionResults(),
    authenticatorAttachment: (cred as any).authenticatorAttachment,
  };
}

/** Register a new passkey for the current (authenticated) user. */
export async function registerPasskey(name: string, token: string): Promise<void> {
  const options = await postJson<any>('/register/options', undefined, token);
  const cred = (await navigator.credentials.create({
    publicKey: decodeCreationOptions(options),
  })) as PublicKeyCredential | null;
  if (!cred) throw new Error('Passkey creation cancelled');
  await postJson('/register/verify', { credential: serializeRegistration(cred), name }, token);
}

/** Passwordless login with a discoverable passkey. Sets the session cookie. */
export async function loginWithPasskey(): Promise<void> {
  const options = await postJson<any>('/authenticate/options');
  const challengeId = options.challenge_id;
  const cred = (await navigator.credentials.get({
    publicKey: decodeRequestOptions(options),
  })) as PublicKeyCredential | null;
  if (!cred) throw new Error('Passkey login cancelled');
  await postJson('/authenticate/verify', {
    credential: serializeAssertion(cred),
    challenge_id: challengeId,
  });
}

export interface PasskeyInfo {
  id: string;
  name: string;
  created_at: string | null;
  last_used: string | null;
}

export async function listPasskeys(token: string): Promise<PasskeyInfo[]> {
  const res = await fetch(`${API_BASE}/credentials`, {
    headers: { Authorization: `Bearer ${token}` },
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to load passkeys');
  return res.json();
}

export async function renamePasskey(id: string, name: string, token: string): Promise<void> {
  const res = await fetch(`${API_BASE}/credentials/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    credentials: 'include',
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error('Failed to rename passkey');
}

export async function deletePasskey(id: string, token: string): Promise<void> {
  const res = await fetch(`${API_BASE}/credentials/${id}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to delete passkey');
}
