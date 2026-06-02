export type Role = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  pending?: boolean;
  error?: string | null;
  startedAt?: number;
  endedAt?: number;
  promptChars?: number;
}

export interface FocusInfo {
  id: string;
  label: string;
  display: string;
}

export type SuggestionGroup = { group: string; items: string[] };
