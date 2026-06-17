import { Flag, TrendingUp, Brain, Gavel } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export type SectionId = 'command' | 'strategy' | 'intel' | 'governance';

export interface SectionDef {
  id: SectionId;
  icon: LucideIcon;
  /** i18n key for the label. */
  labelKey: string;
}

export const SECTIONS: SectionDef[] = [
  { id: 'command', icon: Flag, labelKey: 'nav_command' },
  { id: 'strategy', icon: TrendingUp, labelKey: 'nav_strategy' },
  { id: 'intel', icon: Brain, labelKey: 'nav_intel' },
  { id: 'governance', icon: Gavel, labelKey: 'nav_governance' },
];
