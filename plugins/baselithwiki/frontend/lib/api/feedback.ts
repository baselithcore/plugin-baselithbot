import { authFetch } from './client';

export interface FeedbackPayload {
  message_id: string;
  rating: 'up' | 'down';
  reason?: string;
  question?: string;
  answer?: string;
  sources?: Array<{ document_id: string; title: string; score?: number }>;
  edition?: string;
  at?: number;
}

/**
 * Invia feedback al backend. Fire-and-forget: UX non blocca.
 * Failure silenziosa (localStorage ha già catturato il voto).
 *
 * Usa ``authFetch`` per iniettare il bearer JWT: in modalità Postgres
 * il router `/api/feedback` chiama `require_user` e rifiuterebbe 401
 * una POST senza header — il vote sparirebbe sia da DB che da JSONL.
 */
export async function submitFeedback(payload: FeedbackPayload): Promise<void> {
  try {
    const res = await authFetch('/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      // eslint-disable-next-line no-console
      console.warn('[feedback] POST failed', res.status, await res.text().catch(() => ''));
    }
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('[feedback] network error', err);
  }
}
