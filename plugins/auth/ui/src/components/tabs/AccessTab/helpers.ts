/** Pure helpers for the Access Control screen: tab-permission slug, plugin
 * name humanization, and grouping discovered tabs by their owning plugin. */

import type { TabPolicy } from '../../../types';

export const tabSlug = (plugin: string, tabId: string) => `tab:${plugin}:${tabId}`;

/** "baselith_pitwall" -> "Baselith Pitwall". */
export function humanizePlugin(slug: string): string {
  return slug
    .replace(/[_\-.]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export interface PluginGroupData {
  plugin: string;
  label: string;
  tabs: TabPolicy[];
}

/** Group tabs by plugin, alphabetically, tabs sorted by label within. */
export function groupByPlugin(tabs: TabPolicy[]): PluginGroupData[] {
  const map = new Map<string, TabPolicy[]>();
  for (const tab of tabs) {
    const list = map.get(tab.plugin) ?? [];
    list.push(tab);
    map.set(tab.plugin, list);
  }
  return [...map.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([plugin, list]) => ({
      plugin,
      label: humanizePlugin(plugin),
      tabs: [...list].sort((a, b) => a.label.localeCompare(b.label)),
    }));
}

/** Case-insensitive match of a tab against a search query (label or plugin). */
export function matchesQuery(tab: TabPolicy, label: string, q: string): boolean {
  if (!q) return true;
  const needle = q.toLowerCase();
  return (
    tab.label.toLowerCase().includes(needle) ||
    tab.plugin.toLowerCase().includes(needle) ||
    label.toLowerCase().includes(needle)
  );
}
