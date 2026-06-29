/**
 * Console theme hook — light / dark / system, persisted and OS-aware.
 *
 * Mirrors the resolved theme onto `<html data-theme>` (so body-portaled menus
 * theme too) while the scoped token overrides live on the `.console` wrapper —
 * matching the auth console so the compliance plugin reads as the same product.
 * The shared `@auth/login` wall never reads `data-theme`, so it stays untouched.
 */

import { useCallback, useEffect, useState } from 'react';

export type ThemePref = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

const STORAGE_KEY = 'comp_theme';

const systemTheme = (): ResolvedTheme =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches
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
  toggle: () => void;
}

export function useTheme(): ThemeApi {
  const [pref, setPref] = useState<ThemePref>(readPref);
  const [resolved, setResolved] = useState<ResolvedTheme>(() =>
    pref === 'system' ? systemTheme() : pref,
  );

  useEffect(() => {
    if (pref === 'system') localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, pref);
    setResolved(pref === 'system' ? systemTheme() : pref);
  }, [pref]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', resolved);
  }, [resolved]);

  useEffect(() => {
    if (pref !== 'system' || !window.matchMedia) return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = (e: MediaQueryListEvent) => setResolved(e.matches ? 'dark' : 'light');
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, [pref]);

  const toggle = useCallback(() => setPref(resolved === 'dark' ? 'light' : 'dark'), [resolved]);

  return { pref, resolved, toggle };
}
