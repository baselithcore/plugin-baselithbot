import { useTranslation } from 'react-i18next';

// Compact EN/IT toggle; persists via i18next language detector.
export function LangSwitch() {
  const { i18n } = useTranslation();
  const lng = i18n.resolvedLanguage === 'it' ? 'it' : 'en';
  return (
    <div className="flex items-center gap-0.5 rounded-lg border border-hair bg-surface-2 p-0.5 text-xs">
      {(['en', 'it'] as const).map((code) => (
        <button
          key={code}
          onClick={() => void i18n.changeLanguage(code)}
          className={`rounded-md px-2 py-1 font-semibold uppercase tracking-wide transition ${
            lng === code ? 'bg-info/15 text-info' : 'text-faint hover:text-ink'
          }`}
        >
          {code}
        </button>
      ))}
    </div>
  );
}
