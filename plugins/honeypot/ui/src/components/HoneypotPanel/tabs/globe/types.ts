/**
 * Type definitions for Globe Tab components
 */

import type { AttackEvent, HoneypotInfo, HoneypotAttacker } from '../../../types';

/**
 * Props for the main GlobeTab component
 */
export interface GlobeTabProps {
  events: AttackEvent[];
  activeProtocols: string[];
  onSelectAttack: (event: AttackEvent) => void;
  honeypots: HoneypotInfo[];
  selectedHoneypotId: string | null;
  onSelectHoneypot: (honeypotId: string) => void;
  honeypotsLoading?: boolean;
  attackers?: HoneypotAttacker[];
  isActive?: boolean;
  timeRange: string;
  onTimeRangeChange: (range: string) => void;
}

/**
 * Filter type for bot/human classification
 */
export type FilterType = 'all' | 'human' | 'bot';

/**
 * Unified display item combining events and attackers
 */
export interface DisplayItem {
  type: 'event' | 'attacker';
  data: AttackEvent | HoneypotAttacker;
  id: string;
  ip: string;
  country: string;
  city: string;
  protocol: string;
  severity: string;
  timestamp: string;
  is_bot: boolean;
  confidence: number;
}

/**
 * Autocomplete suggestion item
 */
export interface SearchSuggestion {
  type: 'ip' | 'country' | 'city';
  value: string;
}
