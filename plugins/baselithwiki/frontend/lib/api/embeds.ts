/**
 * Embeds admin API client (mig 017).
 *
 * Endpoint montati a ``/api/admin/embeds/*``. Gating server-side via
 * ``require_permission(admin.embed.manage)``. Embed token in plaintext
 * arriva SOLO nelle response di ``create`` e ``rotateToken`` — mai
 * leggibile dopo (token_hash storato server-side).
 */

import { json } from './client';

export interface EmbedTheme {
  primary?: string;
  background?: string;
  text?: string;
  position?: 'bottom-right' | 'bottom-left';
  font?: string;
  width?: string;
  height?: string;
}

export interface EmbedSummary {
  id: string;
  slug: string;
  name: string;
  description: string;
  tenant_id: string;
  token_prefix: string;
  origin_allowlist: string[];
  theme: EmbedTheme;
  welcome_message: string;
  suggested_questions: string[];
  rate_limit_per_minute: number;
  is_enabled: boolean;
  created_by: string | null;
  last_used_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface EmbedWithToken extends EmbedSummary {
  embed_token: string;
}

export interface CreateEmbedArgs {
  slug: string;
  name: string;
  description?: string;
  origin_allowlist?: string[];
  theme?: EmbedTheme;
  welcome_message?: string;
  suggested_questions?: string[];
  rate_limit_per_minute?: number;
}

export interface UpdateEmbedArgs {
  name?: string;
  description?: string;
  origin_allowlist?: string[];
  theme?: EmbedTheme;
  welcome_message?: string;
  suggested_questions?: string[];
  rate_limit_per_minute?: number;
  is_enabled?: boolean;
}

const BASE_PATH = '/admin/embeds';

export const listEmbeds = (): Promise<EmbedSummary[]> => json(BASE_PATH);

export const createEmbed = (args: CreateEmbedArgs): Promise<EmbedWithToken> =>
  json(BASE_PATH, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(args),
  });

export const getEmbed = (embedId: string): Promise<EmbedSummary> =>
  json(`${BASE_PATH}/${encodeURIComponent(embedId)}`);

export const updateEmbed = (embedId: string, args: UpdateEmbedArgs): Promise<EmbedSummary> =>
  json(`${BASE_PATH}/${encodeURIComponent(embedId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(args),
  });

export const deleteEmbed = (embedId: string): Promise<{ status: string; removed: boolean }> =>
  json(`${BASE_PATH}/${encodeURIComponent(embedId)}`, { method: 'DELETE' });

export const rotateToken = (embedId: string): Promise<EmbedWithToken> =>
  json(`${BASE_PATH}/${encodeURIComponent(embedId)}/rotate-token`, {
    method: 'POST',
  });
