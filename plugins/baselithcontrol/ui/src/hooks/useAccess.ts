import { useCallback, useEffect } from 'react';
import { fetchAccessibleTabs } from '@/lib/api';
import { useControlStore } from '@/store/useControlStore';
import type { AccessibleTab } from '@/types';

const PLUGIN = 'baselithcontrol';

/**
 * Decide whether the caller may see a given dashboard tab.
 *
 * Default-allow: while the policy is still loading (null) or a tab is unmanaged
 * (absent from the policy), access is granted — restriction is strictly opt-in
 * and a transient fetch failure must never hide the whole dashboard.
 */
export function canAccessTab(tabId: string, tabs: AccessibleTab[] | null): boolean {
  if (tabs === null) return true;
  const matches = tabs.filter((t) => t.tab_id === tabId && t.plugin === PLUGIN);
  if (matches.length === 0) return true;
  return matches.some((t) => t.allowed);
}

/**
 * Load the central per-tab access policy once and keep the active tab legal:
 * if the current tab becomes inaccessible, fall back to the first allowed one.
 */
export function useAccess(): void {
  const setAccessibleTabs = useControlStore((s) => s.setAccessibleTabs);
  const accessibleTabs = useControlStore((s) => s.accessibleTabs);
  const currentTab = useControlStore((s) => s.currentTab);
  const setTab = useControlStore((s) => s.setTab);

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
    if (canAccessTab(currentTab, accessibleTabs)) return;
    const fallback = (['dashboard', 'events', 'system'] as const).find((id) =>
      canAccessTab(id, accessibleTabs)
    );
    if (fallback && fallback !== currentTab) setTab(fallback);
  }, [accessibleTabs, currentTab, setTab]);
}

/** Reactive selector returning a `(tabId) => boolean` access predicate. */
export function useCanAccessTab(): (tabId: string) => boolean {
  const accessibleTabs = useControlStore((s) => s.accessibleTabs);
  return useCallback((tabId: string) => canAccessTab(tabId, accessibleTabs), [accessibleTabs]);
}

/**
 * Decide whether a whole plugin (its card in the grid + any of its surfaces)
 * should be visible to the caller.
 *
 * Default-allow, mirroring {@link canAccessTab}: a plugin with no policy entries
 * is unmanaged and stays visible; a managed plugin is visible only if AT LEAST
 * ONE of its tabs is allowed (so a multi-tab plugin is hidden only when every
 * tab is denied). The card name equals the policy `plugin` key (both the
 * manifest name), so matching is exact. Honors impersonation because the policy
 * is fetched with the shared Bearer.
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
