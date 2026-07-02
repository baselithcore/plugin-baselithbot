import { useCallback, useEffect } from 'react';
import { useAuth } from '@auth';
import { fetchAccessibleTabs } from '@/lib/api';
import { TAB_IDS, useControlStore } from '@/store/useControlStore';
import type { AccessibleTab } from '@/types';

const PLUGIN = 'baselithcontrol';

/**
 * Keep the active tab legal against the central per-tab access policy.
 *
 * Tab-level checks delegate to the already-mounted `@auth` context
 * (`useAuth().canAccessTab`) — the single default-allow policy every plugin
 * shares — instead of re-implementing it locally. The raw policy list is still
 * fetched once into the store, but only for the plugin-level visibility
 * aggregation below (the @auth context does not expose the raw list).
 */
export function useAccess(): void {
  const setAccessibleTabs = useControlStore((s) => s.setAccessibleTabs);
  const currentTab = useControlStore((s) => s.currentTab);
  const setTab = useControlStore((s) => s.setTab);
  const { canAccessTab } = useAuth();

  useEffect(() => {
    let alive = true;
    fetchAccessibleTabs().then((tabs) => {
      if (alive) setAccessibleTabs(tabs);
    });
    return () => {
      alive = false;
    };
  }, [setAccessibleTabs]);

  useEffect(() => {
    if (canAccessTab(currentTab, PLUGIN)) return;
    // Fall back across the FULL tab list (nav order) so a user whose only
    // allowed tab is e.g. 'logs' still lands somewhere legal.
    const fallback = TAB_IDS.find((id) => canAccessTab(id, PLUGIN));
    if (fallback && fallback !== currentTab) setTab(fallback);
  }, [canAccessTab, currentTab, setTab]);
}

/** Reactive `(tabId) => boolean` predicate backed by the central @auth policy. */
export function useCanAccessTab(): (tabId: string) => boolean {
  const { canAccessTab } = useAuth();
  return useCallback((tabId: string) => canAccessTab(tabId, PLUGIN), [canAccessTab]);
}

/**
 * Decide whether a whole plugin (its card in the grid + any of its surfaces)
 * should be visible to the caller.
 *
 * Default-allow, mirroring the central `canAccessTab`: a plugin with no policy
 * entries is unmanaged and stays visible; a managed plugin is visible only if
 * AT LEAST ONE of its tabs is allowed (so a multi-tab plugin is hidden only
 * when every tab is denied). The card name equals the policy `plugin` key
 * (both the manifest name), so matching is exact. Honors impersonation because
 * the policy is fetched with the shared Bearer.
 */
export function canAccessPlugin(pluginName: string, tabs: AccessibleTab[] | null): boolean {
  if (tabs === null) return true;
  const matches = tabs.filter((t) => t.plugin === pluginName);
  if (matches.length === 0) return true;
  return matches.some((t) => t.allowed);
}

/** Reactive selector returning a `(pluginName) => boolean` access predicate. */
export function useCanAccessPlugin(): (pluginName: string) => boolean {
  const accessibleTabs = useControlStore((s) => s.accessibleTabs);
  return useCallback(
    (pluginName: string) => canAccessPlugin(pluginName, accessibleTabs),
    [accessibleTabs]
  );
}
