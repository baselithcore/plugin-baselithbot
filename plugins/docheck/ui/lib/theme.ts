'use client';

import { useEffect, useState } from 'react';

export type Theme = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

export const THEME_STORAGE_KEY = 'docheck-theme';
export const DEFAULT_THEME: Theme = 'light';

export function resolveTheme(theme: Theme): ResolvedTheme {
  if (theme === 'system') {
    if (typeof window === 'undefined') return 'light';
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return theme;
}

export function applyTheme(theme: Theme): ResolvedTheme {
  const resolved = resolveTheme(theme);
  const root = document.documentElement;
  root.classList.toggle('dark', resolved === 'dark');
  root.dataset.theme = resolved;
  root.style.colorScheme = resolved;
  return resolved;
}

export function getStoredTheme(): Theme {
  if (typeof window === 'undefined') return DEFAULT_THEME;
  const raw = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (raw === 'light' || raw === 'dark' || raw === 'system') return raw;
  return DEFAULT_THEME;
}

export function setStoredTheme(theme: Theme) {
  window.localStorage.setItem(THEME_STORAGE_KEY, theme);
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(DEFAULT_THEME);
  const [resolved, setResolved] = useState<ResolvedTheme>('light');

  useEffect(() => {
    const stored = getStoredTheme();
    setThemeState(stored);
    setResolved(applyTheme(stored));

    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => {
      if (getStoredTheme() === 'system') setResolved(applyTheme('system'));
    };
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, []);

  function setTheme(next: Theme) {
    setStoredTheme(next);
    setThemeState(next);
    setResolved(applyTheme(next));
  }

  return { theme, resolvedTheme: resolved, setTheme };
}

/**
 * Inline script executed before paint to set the theme class on <html>,
 * avoiding a FOUC. Light is the default; only switch to dark if the user
 * explicitly chose it or chose "system" with a dark OS preference.
 */
export const THEME_INIT_SCRIPT = `
(function() {
  try {
    var k = '${THEME_STORAGE_KEY}';
    var t = localStorage.getItem(k) || '${DEFAULT_THEME}';
    var dark = t === 'dark' || (t === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
    var r = document.documentElement;
    if (dark) r.classList.add('dark'); else r.classList.remove('dark');
    r.dataset.theme = dark ? 'dark' : 'light';
    r.style.colorScheme = dark ? 'dark' : 'light';
  } catch (_) {}
})();
`;
