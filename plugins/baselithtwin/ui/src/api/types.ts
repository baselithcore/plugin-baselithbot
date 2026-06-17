// Wire types mirroring the backend Pydantic models. Kept in one place so the
// API client and components share a single source of truth for the contract.

export type ReplyStatus = 'draft' | 'queued' | 'auto_sent' | 'approved' | 'rejected' | 'failed';

export interface TwinStatus {
  owner_name: string;
  autonomy: 'suggest' | 'whitelist' | 'full';
  gateway: string;
  gateway_connected: boolean;
  style_trained: boolean;
  style_messages: number;
  whitelist_size: number;
  pending_replies: number;
  salient_facts: number;
  paused: boolean;
  version: string;
}

export type AuditAction =
  | 'reply.approved'
  | 'reply.rejected'
  | 'reply.auto_sent'
  | 'reply.send_failed'
  | 'whitelist.added'
  | 'whitelist.removed'
  | 'fact.curated'
  | 'style.trained'
  | 'twin.paused'
  | 'twin.resumed'
  | 'webhook.rejected';

export interface AuditEvent {
  id: string;
  action: AuditAction;
  actor: string;
  resource?: string | null;
  success: boolean;
  ip_address?: string | null;
  details: Record<string, unknown>;
  at: string;
}

export interface StyleMetrics {
  avg_message_chars: number;
  avg_words_per_message: number;
  emoji_rate: number;
  question_rate: number;
  exclamation_rate: number;
  uppercase_ratio: number;
  formality: number;
  top_emojis: string[];
  top_expressions: string[];
  dominant_locale: string;
}

export interface StyleProfile {
  owner_id: string;
  sample_size: number;
  trained: boolean;
  metrics: StyleMetrics;
  exemplars: { text: string; contact_id?: string | null }[];
  updated_at: string;
}

export interface DraftReply {
  contact_id: string;
  in_reply_to: string;
  text: string;
  confidence: number;
  style_applied: boolean;
  degraded: boolean;
  rationale?: string | null;
}

export interface PendingReply {
  id: string;
  contact_id: string;
  in_reply_to: string;
  inbound_text: string;
  draft: DraftReply;
  status: ReplyStatus;
  created_at: string;
  decided_at?: string | null;
  decided_by?: string | null;
}

export interface WhitelistEntry {
  contact_id: string;
  display_name?: string | null;
  note?: string | null;
  added_at: string;
}

export interface SalientFact {
  id: string;
  contact_id: string;
  text: string;
  salience: number;
  tags: string[];
  source_message_id?: string | null;
  created_at: string;
}

export interface StreamEvent {
  type: string;
  payload: Record<string, unknown>;
  at: string;
}
