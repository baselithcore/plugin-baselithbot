/**
 * CVEHunterPanel - Utility Functions
 */

import type { CVEAgentStatus } from '../types';

/**
 * Get CSS class based on severity level
 */
export const getSeverityClass = (severity: string): string => {
  return severity?.toLowerCase() || 'low';
};

/**
 * Parsed CVSS Metric
 */
export interface CVSSMetric {
  label: string;
  value: string;
  score: string;
  color: string;
}

/**
 * Parse CVSS Vector String (v3.1)
 * Example: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
 */
export const parseCVSSVector = (vector: string | null): CVSSMetric[] => {
  if (!vector) return [];

  // Remove version prefix if present
  const cleanVector = vector.replace(/^CVSS:\d\.\d\//, '');
  const parts = cleanVector.split('/');

  const metrics: CVSSMetric[] = [];

  const metricMap: Record<string, { label: string; values: Record<string, string> }> = {
    AV: {
      label: 'Attack Vector',
      values: { N: 'Network', A: 'Adjacent', L: 'Local', P: 'Physical' },
    },
    AC: {
      label: 'Attack Complexity',
      values: { L: 'Low', H: 'High' },
    },
    PR: {
      label: 'Privileges Required',
      values: { N: 'None', L: 'Low', H: 'High' },
    },
    UI: {
      label: 'User Interaction',
      values: { N: 'None', R: 'Required' },
    },
    S: {
      label: 'Scope',
      values: { U: 'Unchanged', C: 'Changed' },
    },
    C: {
      label: 'Confidentiality',
      values: { H: 'High', L: 'Low', N: 'None' },
    },
    I: {
      label: 'Integrity',
      values: { H: 'High', L: 'Low', N: 'None' },
    },
    A: {
      label: 'Availability',
      values: { H: 'High', L: 'Low', N: 'None' },
    },
  };

  parts.forEach((part) => {
    const [key, val] = part.split(':');
    if (metricMap[key] && metricMap[key].values[val]) {
      const label = metricMap[key].label;
      const value = metricMap[key].values[val];
      let color = 'var(--text-secondary)';

      // specialized coloring logic
      if (['C', 'I', 'A'].includes(key)) {
        if (val === 'H') color = 'var(--cyber-danger)';
        else if (val === 'L') color = 'var(--cyber-warning)';
      } else if (key === 'AV' && val === 'N') {
        color = 'var(--cyber-danger)';
      }

      metrics.push({ label, value, score: val, color });
    }
  });

  return metrics;
};

/**
 * Get emoji icon for agent type
 */
export const getAgentIcon = (type: string): string => {
  switch (type) {
    case 'scanner':
      return '🔍';
    case 'analyzer':
      return '🧠';
    case 'discovery':
      return '🕵️';
    default:
      return '🤖';
  }
};

/**
 * Calculate agent activity percentage based on status
 */
export const getAgentActivity = (agent: CVEAgentStatus): number => {
  switch (agent.status) {
    case 'scanning':
      return 85;
    case 'analyzing':
      return 60;
    case 'discovering':
      return 45;
    case 'error':
      return 10;
    default:
      return 0;
  }
};

/**
 * Truncate text to specified max length with ellipsis
 */
export const truncateText = (value: string, max = 60): string => {
  if (!value) return '';
  return value.length > max ? `${value.slice(0, max)}...` : value;
};

/**
 * Default demo agents for initial render
 */
export const DEFAULT_AGENTS: CVEAgentStatus[] = [
  {
    agent_id: 'scanner-1',
    agent_type: 'scanner',
    status: 'idle',
    current_task: null,
    tasks_completed: 0,
    tasks_failed: 0,
    last_active: null,
    error_message: null,
  },
  {
    agent_id: 'analyzer-1',
    agent_type: 'analyzer',
    status: 'idle',
    current_task: null,
    tasks_completed: 0,
    tasks_failed: 0,
    last_active: null,
    error_message: null,
  },
  {
    agent_id: 'discovery-1',
    agent_type: 'discovery',
    status: 'idle',
    current_task: null,
    tasks_completed: 0,
    tasks_failed: 0,
    last_active: null,
    error_message: null,
  },
];
