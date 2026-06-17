import { create } from 'zustand';

export type Theme = 'dark' | 'light';

const STORAGE_KEY = 'blc.theme';

function initial(): Theme {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === 'light' || saved === 'dark') return saved;
  // Light-first: only honor an explicit OS *dark* preference on first run.
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function apply(theme: Theme): void {
  document.documentElement.setAttribute('data-theme', theme);
}

interface ThemeStore {
  theme: Theme;
  toggle: () => void;
}

export const useTheme = create<ThemeStore>((set, get) => ({
  theme: initial(),
  toggle: () => {
    const next: Theme = get().theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem(STORAGE_KEY, next);
    apply(next);
    set({ theme: next });
  },
}));

// Apply the resolved theme to <html> as soon as the module loads.
apply(useTheme.getState().theme);
