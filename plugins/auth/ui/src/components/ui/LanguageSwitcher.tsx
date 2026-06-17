/**
 * Compact language switcher (EN / IT). Persists via the i18n detector cache.
 */

import { useTranslation } from 'react-i18next';
import { Languages } from 'lucide-react';
import { SUPPORTED_LANGUAGES } from '../../i18n';

export default function LanguageSwitcher() {
  const { i18n, t } = useTranslation();
  const current = (i18n.resolvedLanguage || 'en').slice(0, 2);

  return (
    <div className="lang-switcher" title={t('language.label')}>
      <Languages size={16} />
      {SUPPORTED_LANGUAGES.map((lng) => (
        <button
          key={lng}
          type="button"
          className={`lang-btn ${current === lng ? 'active' : ''}`}
          onClick={() => i18n.changeLanguage(lng)}
          aria-pressed={current === lng}
        >
          {lng.toUpperCase()}
        </button>
      ))}
      <style>{`
        .lang-switcher { display: inline-flex; align-items: center; gap: 0.25rem;
          color: var(--admin-text-muted, #94a3b8); }
        .lang-btn { font-size: 0.7rem; font-weight: 600; padding: 0.15rem 0.4rem;
          border-radius: 0.3rem; border: 1px solid transparent; background: transparent;
          color: var(--admin-text-muted, #94a3b8); cursor: pointer; }
        .lang-btn.active { background: var(--admin-accent, #3b5bdb); color: #fff; }
      `}</style>
    </div>
  );
}
