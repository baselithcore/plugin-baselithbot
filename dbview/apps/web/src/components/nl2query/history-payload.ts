import { NL2_HISTORY_MAX_TURNS, type Nl2ConversationTurn } from '@dbview/shared';
import type { ChatTurn } from './turn-types.js';

/**
 * Number of prior turns replayed to the backend on each follow-up request.
 *
 * Kept tighter than `NL2_HISTORY_MAX_TURNS` (the server-side ceiling) so that
 * the prompt budget on small local models (e.g. 7B Ollama) stays modest while
 * still covering common multi-turn patterns ("now filter by X", "and the
 * previous one"). Bump only if anaphora reaches further than 4 turns back.
 */
export const HISTORY_WINDOW = Math.min(4, NL2_HISTORY_MAX_TURNS);

/**
 * Slice the most recent `HISTORY_WINDOW` completed turns into the compact
 * payload the backend expects. Only turns that produced a translation are
 * included — pending / errored turns carry no usable SQL and would just
 * confuse the model. Result rows are intentionally omitted (privacy + tokens).
 */
export function buildHistoryPayload(conversation: readonly ChatTurn[]): Nl2ConversationTurn[] {
  const usable = conversation.filter(
    (t) => t.status === 'ready' && t.translation && t.translation.query,
  );
  return usable.slice(-HISTORY_WINDOW).map((t) => ({
    prompt: t.prompt,
    query: t.translation!.query,
    language: t.translation!.language,
    rowCount: t.result?.rowCount ?? null,
    ok: !t.executionError,
  }));
}
