// Language switcher — toggles the i18n locale and persists it (via the detector
// cache). Required by the mandatory en+it i18n contract.

import { useTranslation } from 'react-i18next';
import { Languages } from 'lucide-react';

const LOCALES = [
  { code: 'en', label: 'EN' },
  { code: 'it', label: 'IT' },
];

export function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const active = i18n.language?.slice(0, 2) ?? 'en';
  return (
    <div className="flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 p-0.5">
      <Languages className="ml-1.5 h-3.5 w-3.5 text-white/40" aria-hidden />
      {LOCALES.map((l) => (
        <button
          key={l.code}
          onClick={() => void i18n.changeLanguage(l.code)}
          aria-pressed={active === l.code}
          className={`rounded-md px-2 py-1 text-xs font-medium transition-colors ${
            active === l.code ? 'bg-brand-500 text-ink-900' : 'text-white/60 hover:text-white'
          }`}
        >
          {l.label}
        </button>
      ))}
    </div>
  );
}
