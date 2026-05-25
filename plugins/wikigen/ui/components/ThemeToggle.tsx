import { Monitor, Moon, Sun } from 'lucide-react';
import { useEffect, useState } from 'react';
import { cn } from '../lib/cn';

export type Theme = 'light' | 'dark' | 'auto';

const STORAGE_KEY = 'llm-wiki:theme';

function readTheme(): Theme {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === 'light' || v === 'dark' || v === 'auto') return v;
  } catch {
    /* storage disabled */
  }
  return 'auto';
}

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  root.classList.remove('light', 'dark');
  if (theme === 'light' || theme === 'dark') {
    root.classList.add(theme);
  }
  // Aggiorna meta color-scheme perché UA browser usi colori coerenti
  const meta = document.querySelector('meta[name="color-scheme"]');
  if (meta) {
    const scheme = theme === 'auto' ? 'light dark' : theme === 'dark' ? 'dark' : 'light';
    meta.setAttribute('content', scheme);
  }
}

export function initTheme() {
  applyTheme(readTheme());
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() => readTheme());

  useEffect(() => {
    applyTheme(theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      /* storage disabled */
    }
  }, [theme]);

  const options: { id: Theme; icon: typeof Sun; label: string }[] = [
    { id: 'light', icon: Sun, label: 'chiaro' },
    { id: 'auto', icon: Monitor, label: 'sistema' },
    { id: 'dark', icon: Moon, label: 'scuro' },
  ];

  return (
    <div
      role="radiogroup"
      aria-label="tema interfaccia"
      className="inline-flex rounded-full border border-[var(--color-border)] bg-[var(--color-canvas-raised)] p-0.5"
    >
      {options.map((o) => (
        <button
          key={o.id}
          role="radio"
          aria-checked={theme === o.id}
          onClick={() => setTheme(o.id)}
          title={`tema ${o.label}`}
          className={cn(
            'focus-ring inline-flex items-center justify-center rounded-full p-1 transition-colors',
            theme === o.id ? 'bg-[var(--color-brand)] text-white' : 'text-ink-subtle hover:text-ink'
          )}
        >
          <o.icon size={12} />
        </button>
      ))}
    </div>
  );
}
