/**
 * Minimal en/it language switcher for the wiki shell.
 *
 * Persists the choice via i18next's localStorage detector (key ``i18nextLng``),
 * which is the same key the shared ``@auth`` login UI reads — so the login wall
 * and the wiki render in the same language.
 */

import { useTranslation } from 'react-i18next';

const LANGS: { code: 'en' | 'it'; label: string }[] = [
  { code: 'en', label: 'EN' },
  { code: 'it', label: 'IT' },
];

export function LanguageSwitcher({ className }: { className?: string }) {
  const { i18n, t } = useTranslation();
  const active = (i18n.resolvedLanguage ?? 'en').slice(0, 2);

  return (
    <div
      className={className}
      role="group"
      aria-label={t('shell.language')}
      style={{ display: 'inline-flex', gap: 4 }}
    >
      {LANGS.map(({ code, label }) => (
        <button
          key={code}
          type="button"
          onClick={() => void i18n.changeLanguage(code)}
          aria-pressed={active === code}
          className={cnLang(active === code)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function cnLang(activeState: boolean): string {
  return [
    'rounded-md px-2 py-1 text-xs font-semibold transition-colors',
    activeState
      ? 'bg-accent/15 text-accent'
      : 'text-ink-soft hover:text-ink hover:bg-surface-2',
  ].join(' ');
}
