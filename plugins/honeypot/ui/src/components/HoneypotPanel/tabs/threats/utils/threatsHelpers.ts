/**
 * threatsHelpers - Utility functions for ThreatsTab
 * Provides autocomplete suggestions and filter building logic
 */

import { AttackEvent } from '../../../../types';

export interface FilterState {
  source_ip: string;
  country: string;
  honeypot_id: string;
  protocol: string;
  severity: string;
  category: string;
  is_bot: boolean | undefined;
}

/**
 * Get IP autocomplete suggestions from current events
 */
export function getIpSuggestions(events: AttackEvent[], searchTerm: string): string[] {
  if (!searchTerm || searchTerm.length < 1) return [];

  const term = searchTerm.toLowerCase();
  const seen = new Set<string>();
  const suggestions: string[] = [];

  events.forEach((e) => {
    if (e.source_ip.toLowerCase().includes(term) && !seen.has(e.source_ip)) {
      suggestions.push(e.source_ip);
      seen.add(e.source_ip);
    }
  });

  return suggestions.slice(0, 5);
}

/**
 * Get country autocomplete suggestions from current events
 */
export function getCountrySuggestions(
  events: AttackEvent[],
  searchTerm: string
): { name: string; code: string }[] {
  if (!searchTerm || searchTerm.length < 1) return [];

  const term = searchTerm.toLowerCase();
  const seen = new Set<string>();
  const suggestions: { name: string; code: string }[] = [];

  events.forEach((e) => {
    const name = e.geo?.country || '';
    const code = e.geo?.country_code || '';
    const match = name.toLowerCase().includes(term) || code.toLowerCase().includes(term);

    if (match && code && !seen.has(code)) {
      suggestions.push({ name, code });
      seen.add(code);
    }
  });

  return suggestions.slice(0, 5);
}

/**
 * Build active filters object for API call
 * Removes empty values and normalizes data
 */
export function buildActiveFilters(filters: FilterState): Record<string, any> {
  const activeFilters: Record<string, any> = {};

  if (filters.source_ip) activeFilters.source_ip = filters.source_ip;
  if (filters.country) activeFilters.country = filters.country.toUpperCase();
  if (filters.honeypot_id) activeFilters.honeypot_id = filters.honeypot_id;
  if (filters.protocol) activeFilters.protocol = filters.protocol;
  if (filters.severity) activeFilters.severity = filters.severity;
  if (filters.category) activeFilters.category = filters.category;
  if (filters.is_bot !== undefined) activeFilters.is_bot = filters.is_bot;

  return activeFilters;
}
