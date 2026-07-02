import type { ChatTurn } from './turn-types.js';

const STATUS_COPY_EN: Record<ChatTurn['status'], string> = {
  pending: 'Queuing…',
  translating: 'Drafting query…',
  executing: 'Running query…',
  summarizing: 'Reading results…',
  ready: 'Done',
  error: 'Failed',
};

const STATUS_COPY_IT: Record<ChatTurn['status'], string> = {
  pending: 'In coda…',
  translating: 'Sto preparando la query…',
  executing: 'Sto eseguendo la query…',
  summarizing: 'Sto leggendo i risultati…',
  ready: 'Pronto',
  error: 'Errore',
};

export function statusCopy(locale: 'en' | 'it'): Record<ChatTurn['status'], string> {
  return locale === 'it' ? STATUS_COPY_IT : STATUS_COPY_EN;
}
