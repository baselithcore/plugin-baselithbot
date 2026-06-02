import type { FindingState } from '../../../lib/api';

export interface AttackTechnique {
  id: string;
  name: string;
}

export const STATE_OPTIONS: FindingState[] = ['open', 'triaged', 'fixed', 'wontfix', 'accepted'];
