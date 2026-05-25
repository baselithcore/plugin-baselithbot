/**
 * Graph visualization constants
 */

import type { AttackSeverity } from '../../../../types';

// Vibrant cluster colors
export const CLUSTER_COLORS = [
  '#00ff88', // Green
  '#00d4ff', // Cyan
  '#ff6b9d', // Pink
  '#ffdd00', // Yellow
  '#ff7b00', // Orange
  '#bf5fff', // Purple
  '#00a8ff', // Blue
  '#ff5577', // Coral
];

// Severity colors
export const SEVERITY_COLORS: Record<AttackSeverity, string> = {
  critical: '#ff4757',
  high: '#ff6b6b',
  medium: '#ffa502',
  low: '#2ed573',
  info: '#747d8c',
};
