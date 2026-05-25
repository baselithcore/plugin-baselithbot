/**
 * Utility functions for Globe Tab
 */

import type { AttackEvent, HoneypotAttacker, GraphNode } from '../../../types';
import type { SearchSuggestion } from './types';

/**
 * Get color for protocol badge
 */
export function getProtocolColor(protocol: string): string {
  switch (protocol) {
    case 'ssh':
      return '#ff4757';
    case 'http':
      return '#00d2d3';
    default:
      return '#9d4edd';
  }
}

/**
 * Calculate cutoff time based on time range string
 */
export function calculateCutoffTime(timeRange: string): Date | null {
  const now = new Date();

  if (timeRange === '1h') return new Date(now.getTime() - 60 * 60 * 1000);
  if (timeRange === '24h') return new Date(now.getTime() - 24 * 60 * 60 * 1000);
  if (timeRange === '7d') return new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  if (timeRange === '30d') return new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

  return null; // 'all' means no cutoff
}

/**
 * Generate autocomplete suggestions from events
 */
export function getSuggestions(searchTerm: string, events: AttackEvent[]): SearchSuggestion[] {
  if (!searchTerm || searchTerm.length < 2) return [];

  const term = searchTerm.toLowerCase();
  const suggestions: SearchSuggestion[] = [];
  const seen = new Set<string>();

  events.forEach((e) => {
    // IP
    if (e.source_ip.includes(term) && !seen.has(e.source_ip)) {
      suggestions.push({ type: 'ip', value: e.source_ip });
      seen.add(e.source_ip);
    }
    // Country
    if (e.geo?.country && e.geo.country.toLowerCase().includes(term) && !seen.has(e.geo.country)) {
      suggestions.push({ type: 'country', value: e.geo.country });
      seen.add(e.geo.country);
    }
    // City
    if (e.geo?.city && e.geo.city.toLowerCase().includes(term) && !seen.has(e.geo.city)) {
      suggestions.push({ type: 'city', value: e.geo.city });
      seen.add(e.geo.city);
    }
  });

  return suggestions.slice(0, 6); // Limit results
}

/**
 * Create synthetic event from GraphNode or HoneypotAttacker
 */
export function createSyntheticEvent(
  source: GraphNode | HoneypotAttacker,
  type: 'node' | 'attacker'
): any {
  if (type === 'node') {
    const node = source as GraphNode;
    return {
      event_id: 'agg-' + node.ip,
      session_id: 'agg-session-' + node.ip,
      source_ip: node.ip,
      protocol: node.protocol || 'unknown',
      severity: node.severity || 'info',
      category: 'unknown',
      timestamp: node.lastAttack ? node.lastAttack.toISOString() : new Date().toISOString(),
      geo: {
        country: node.country,
        country_code: node.country_code,
        city: null,
      },
      event_type: 'aggregated',
      raw_data: 'No payload captured - Possible port scan or connection only',
      command: null,
      username: null,
      password: null,
      http_method: null,
      http_path: null,
      http_headers: {},
      http_body: null,
      matched_cves: [],
      matched_cwes: [],
      detected_patterns: [],
      ai_classification: null,
      is_bot: false,
      bot_confidence: 0,
      bot_signals: null,
    };
  } else {
    const attacker = source as HoneypotAttacker;
    return {
      event_id: 'agg-' + attacker.ip,
      session_id: 'agg-session-' + attacker.ip,
      source_ip: attacker.ip,
      protocol: attacker.protocols[0] || 'unknown',
      severity: attacker.max_severity || 'info',
      category: 'unknown',
      timestamp: attacker.last_seen,
      geo: {
        country: attacker.country,
        country_code: attacker.country_code,
        city: attacker.city,
      },
      event_type: 'aggregated',
      raw_data: 'No payload captured - Possible port scan or connection only',
      command: null,
      username: null,
      password: null,
      http_method: null,
      http_path: null,
      http_headers: {},
      http_body: null,
      matched_cves: [],
      matched_cwes: [],
      detected_patterns: [],
      ai_classification: null,
      is_bot: false,
      bot_confidence: 0,
      bot_signals: null,
    };
  }
}
