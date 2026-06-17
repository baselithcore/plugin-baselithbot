import type { ChatMessage, ChatSource, Groundedness, ResearchTraceStep } from '@/lib/types';

/** A rendered chat turn — assistant turns may carry citations or link chips. */
export interface Msg {
  role: 'user' | 'assistant';
  text: string;
  sources?: ChatSource[];
  suggestions?: string[];
  /** Faithfulness verdict for an assistant turn (streamed after the answer). */
  grounding?: Groundedness;
  /** Reasoning trace for a deep-research turn (collapsible in the bubble). */
  trace?: ResearchTraceStep[];
}

/** Map a persisted server turn into the panel's render model. */
export function toMsg(m: ChatMessage): Msg {
  return { role: m.role, text: m.content, sources: m.sources };
}
