/**
 * HoneypotPanel Utility Functions
 */

/**
 * Get CSS class for severity styling
 */
export function getSeverityClass(severity: string): string {
  switch (severity.toLowerCase()) {
    case 'critical':
      return 'severity-critical';
    case 'high':
      return 'severity-high';
    case 'medium':
      return 'severity-medium';
    case 'low':
      return 'severity-low';
    default:
      return 'severity-info';
  }
}

/**
 * Get emoji icon for protocol
 */
export function getProtocolIcon(protocol: string): string {
  switch (protocol.toLowerCase()) {
    case 'ssh':
      return '🔐';
    case 'http':
      return '🌐';
    case 'smtp':
      return '📧';
    case 'ftp':
      return '📂';
    case 'telnet':
      return '📠';
    case 'dns':
      return '🔍';
    default:
      return '📡';
  }
}
