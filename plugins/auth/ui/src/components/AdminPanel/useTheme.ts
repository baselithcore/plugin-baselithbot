/**
 * Console theme hook — light / dark / system, persisted and OS-aware.
 *
 * The resolved theme is mirrored onto `<html data-theme>` so that body-portaled
 * menus (e.g. the UserTable row actions) theme correctly too, while the scoped
 * token overrides live on the `.console` wrapper. The shared `@auth/login` wall
 * never reads `data-theme`, so it stays untouched everywhere it is embedded.
 */

import { useCallback, useEffect, useState } from 'react';

export type ThemePref = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

const STORAGE_KEY = 'auth_theme';

const systemTheme = (): ResolvedTheme =>
  typeof window !== 'undefined' &&
  window.matchMedia?.('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light';

const readPref = (): ThemePref => {
  if (typeof localStorage === 'undefined') return 'system';
  const v = localStorage.getItem(STORAGE_KEY);
  return v === 'light' || v === 'dark' ? v : 'system';
};

export interface ThemeApi {
  pref: ThemePref;
  resolved: ResolvedTheme;
  setTheme: (p: ThemePref) => void;
  toggle: () => void;
}

export function useTheme(): ThemeApi {
  const [pref, setPref] = useState<ThemePref>(readPref);
  const [resolved, setResolved] = useState<ResolvedTheme>(() =>
    pref === 'system' ? systemTheme() : pref,
  );

  // Persist the preference and recompute the effective theme when it changes.
  useEffect(() => {
    if (pref === 'system') localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, pref);
    setResolved(pref === 'system' ? systemTheme() : pref);
  }, [pref]);

  // Mirror the effective theme onto <html> for portals + native color-scheme.
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', resolved);
  }, [resolved]);

  // Follow the OS while in `system` mode.
  useEffect(() => {
    if (pref !== 'system' || !window.matchMedia) return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = (e: MediaQueryListEvent) => setResolved(e.matches ? 'dark' : 'light');
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, [pref]);

  const setTheme = useCallback((p: ThemePref) => setPref(p), []);
  const toggle = useCallback(() => setPref(resolved === 'dark' ? 'light' : 'dark'), [resolved]);

  return { pref, resolved, setTheme, toggle };
}
