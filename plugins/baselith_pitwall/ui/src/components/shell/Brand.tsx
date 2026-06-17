import { useTranslation } from 'react-i18next';

/** Wordmark with a stylised pit-wall chevron mark. */
export function Brand() {
  const { t } = useTranslation();
  return (
    <div className="flex items-center gap-3">
      <span className="relative grid h-9 w-9 place-items-center overflow-hidden rounded-xl border border-hair-strong bg-gradient-to-br from-ember/25 to-surface-2 shadow-[0_0_18px_-6px] shadow-ember">
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden>
          <path
            d="M4 3v18M4 4h11l-2.5 3.5L15 11H4"
            className="stroke-ember"
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
            fill="none"
          />
        </svg>
      </span>
      <div className="leading-tight">
        <h1 className="font-display text-[15px] font-bold tracking-tight text-ink">{t('title')}</h1>
        <p className="text-[11px] text-faint">{t('subtitle')}</p>
      </div>
    </div>
  );
}
