import type { ExecuteQueryResponse, Nl2SqlResponse } from '@dbview/shared';

/** Stage of a single conversation turn. */
export type TurnStatus =
  | 'pending'
  | 'translating'
  | 'executing'
  | 'summarizing'
  | 'ready'
  | 'error';

/**
 * 'ask' = full pipeline (translate → execute → summarize).
 * 'translate' = generate query only (legacy "draft first" mode).
 */
export type TurnMode = 'ask' | 'translate';

export interface ChatTurn {
  id: string;
  prompt: string;
  mode: TurnMode;
  status: TurnStatus;
  translation?: Nl2SqlResponse;
  result?: ExecuteQueryResponse;
  executionError?: { code: string; message: string };
  summary?: string;
  highlights?: string[];
  followUps?: string[];
  totalDurationMs?: number;
  error?: string;
  createdAt: number;
}
