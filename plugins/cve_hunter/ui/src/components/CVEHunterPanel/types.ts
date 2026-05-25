/**
 * CVEHunterPanel - Internal Types
 */

export type TabType = 'monitor' | 'analytics' | 'feed';

export interface CVEHunterPanelProps {
  onCVESelect?: (cve: import('../types').CVERecord) => void;
}

export interface DiscoveryLog {
  timestamp: string;
  message: string;
  is_alert: boolean;
  is_error: boolean;
}

export interface Finding {
  pattern?: string;
  timestamp?: string;
  context?: string;
  confidence?: number;
  source?: string;
}
